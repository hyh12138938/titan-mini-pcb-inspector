/*
 * Titan Board Mini —— 焊盘缺件检测（Ethos-U55 + 自训练 int8 模型）
 *
 * 数据流：
 *   OV5640(640x480 RGB565) -> 裁 ROI -> 缩放到 96x96 RGB -> int8 量化
 *     -> Ethos-U55 推理（1 次约 1 ms） -> 去量化 -> argmax -> 屏上画框 + 串口输出
 *
 * 类别顺序（训练时 ImageFolder 字母序）：
 *   pad_output[0] = no_pad（画面里没有焊盘）  pad_output[1] = pad（检测到焊盘）
 *
 * msh 命令：
 *   roi                查看当前 ROI
 *   roi <边长>          设置 ROI 边长（相机像素，默认 200）
 *   roi <边长> <cx> <cy> 同时设置中心
 *   padstat            打印最近一次的原始输出与置信度
 */
#include <rtthread.h>
#include <rtdevice.h>
#include <board.h>
#include <math.h>
#include <stdlib.h>

#include "hal_data.h"
#include "camera_layer.h"
#include "camera_layer_config.h"
#include <lcd_port.h>
#include "pmu_ethosu.h"

#include "pad_invoke.h"
#include "pad_tensors.h"

#define DBG_TAG     "pad"
#define DBG_LVL     DBG_INFO
#include "rtdbg.h"

#define LED_PIN     BSP_IO_PORT_01_PIN_09
#define KEY_PIN     BSP_IO_PORT_02_PIN_01

#define CAM_WIDTH   640
#define FB_XOFF     ((LCD_WIDTH - CAM_WIDTH) / 2)   /* 80 */
#define FB_YOFF     ((LCD_HEIGHT - CAM_HEIGHT) / 2) /* 0 */
#define CAM_HEIGHT  480

#define ROI_SIZE_DEFAULT   200
#define ROI_SIZE_MIN       32
#define ROI_MAX            480

static volatile int32_t roi_size = ROI_SIZE_DEFAULT;
static volatile int32_t roi_cx   = CAM_WIDTH / 2;
static volatile int32_t roi_cy   = CAM_HEIGHT / 2;

/* 像素 -> int8 的查找表（与训练时的归一化 (x/255-0.5)/0.5 一致） */
static int8_t pix_lut[256];

/* 最近一次推理结果，给 msh 命令看 */
static volatile int32_t dbg_defect_q;
static volatile int32_t dbg_good_q;
static volatile float   dbg_defect_f;
static volatile float   dbg_good_f;
static volatile int32_t dbg_result;      /* 0=defect 1=good */
static volatile int32_t dbg_err;         /* pad_invoke 返回值 */

/* 启动阶段进度标记（供调试器读取，不依赖串口） */
volatile int      g_stage;
volatile unsigned g_frames;

typedef struct
{
    int32_t x1, y1, x2, y2;
} pad_box_t;

/* 训练时的类别顺序（ImageFolder 字母序）：0 = no_pad, 1 = pad */
#define PAD_CLASS_NOPAD  0
#define PAD_CLASS_PAD    1

/* DAVE2D 定点转换宏：与官方 demo 的 yolo_rtthread.h 保持一致 */
#ifndef D2_FIX
#define D2_FIX(px) ((d2_point)((px) << 4))
#endif


/* ---- 无相机兜底：直接往帧缓冲填色（GLCDC 持续扫描，无需 flush） ---- */
extern uint8_t fb_background[][DISPLAY_BUFFER_STRIDE_BYTES_INPUT0 * DISPLAY_VSIZE_INPUT0];
#define FB16 ((uint16_t *)fb_background[0])

static void scr_fill(uint16_t color)
{
    for (uint32_t i = 0; i < (uint32_t)LCD_WIDTH * LCD_HEIGHT; i++)
    {
        FB16[i] = color;
    }
}

static void scr_rect(int32_t x, int32_t y, int32_t w, int32_t h, uint16_t color)
{
    for (int32_t j = y; j < y + h; j++)
    {
        if (j < 0 || j >= LCD_HEIGHT) continue;
        for (int32_t i = x; i < x + w; i++)
        {
            if (i < 0 || i >= LCD_WIDTH) continue;
            FB16[j * LCD_WIDTH + i] = color;
        }
    }
}


/* ---- 相机初始化线程 ---- */
volatile int cam_boot_state;   /* 0=进行中 1=成功 -1=失败 */

static void cam_boot_thread(void *arg)
{
    (void)arg;
    fsp_err_t st = camera_init(false);
    cam_boot_state = (FSP_SUCCESS == st) ? 1 : -1;
}

rt_err_t cam_boot_start(void)
{
    rt_thread_t th = rt_thread_create("camb", cam_boot_thread, RT_NULL, 8192, 12, 10);
    if (th == RT_NULL)
    {
        return -RT_ERROR;
    }
    rt_thread_startup(th);
    return RT_EOK;
}


/* 显示侧增益（不影响模型输入）：把镜头画面提亮后再送屏 */
/* 显示侧处理：64K RGB565->RGB565 查表（每像素一次查表，足够快，不拖帧率）
 * out = clamp((in - black) * gain)，逐通道，白平衡已折进 gain
 */
#define BLACK_R    2           /* of 31 */
#define BLACK_G    6           /* of 63 */
#define BLACK_B    2           /* of 31 */
#define GAIN_R16   36          /* 2.25x，含 +12% 红 */
#define GAIN_G16   31          /* 1.94x */
#define GAIN_B16   32          /* 2.00x，含 +3% 蓝 */

static uint16_t g_disp_lut[65536] BSP_ALIGN_VARIABLE(32) BSP_PLACE_IN_SECTION(".sdram");

static void build_disp_lut(void)
{
    for (uint32_t c = 0; c < 65536u; c++)
    {
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;

        r = (r > BLACK_R) ? (((r - BLACK_R) * GAIN_R16) >> 4) : 0; if (r > 31) r = 31;
        g = (g > BLACK_G) ? (((g - BLACK_G) * GAIN_G16) >> 4) : 0; if (g > 63) g = 63;
        b = (b > BLACK_B) ? (((b - BLACK_B) * GAIN_B16) >> 4) : 0; if (b > 31) b = 31;

        g_disp_lut[c] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

/* rotate 180 deg + apply the display LUT in one pass.
 * the panel is mounted 180 deg rotated (verified by a four-quadrant self test),
 * so we pre-rotate into g_rot and let the panel flip it back to upright. */
static uint16_t g_rot[CAM_WIDTH * CAM_HEIGHT] BSP_ALIGN_VARIABLE(32) BSP_PLACE_IN_SECTION(".sdram");

static void frame_rotate_brighten(const uint16_t *src, uint16_t *dst)
{
    for (int32_t y = 0; y < CAM_HEIGHT; y++)
    {
        const uint16_t *srow = src + (int32_t)(CAM_HEIGHT - 1 - y) * CAM_WIDTH;
        uint16_t *drow = dst + (int32_t)y * CAM_WIDTH;
        for (int32_t x = 0; x < CAM_WIDTH; x++)
        {
            drow[x] = g_disp_lut[srow[(int32_t)(CAM_WIDTH - 1 - x)]];
        }
    }
}

static void build_pix_lut(void)
{
    for (int i = 0; i < 256; i++)
    {
        float v = ((float)i / 255.0f - 0.5f) / 0.5f;             /* [-1,1] */
        int q = (int)lroundf(v / PAD_INPUT_SCALE) + PAD_INPUT_ZP;
        if (q < -128) q = -128;
        if (q >  127) q =  127;
        pix_lut[i] = (int8_t)q;
    }
}

/* RGB565 帧 -> ROI 裁剪 + 缩放到 96x96 RGB + int8 量化 */
static void frame_to_input(const uint16_t *fb)
{
    int32_t half = roi_size / 2;
    int32_t x0 = roi_cx - half;
    int32_t y0 = roi_cy - half;

    for (int y = 0; y < PAD_INPUT_H; y++)
    {
        int32_t sy = y0 + (y * roi_size) / PAD_INPUT_H;
        if (sy < 0)            sy = 0;
        if (sy >= CAM_HEIGHT)  sy = CAM_HEIGHT - 1;

        for (int x = 0; x < PAD_INPUT_W; x++)
        {
            int32_t sx = x0 + (x * roi_size) / PAD_INPUT_W;
            if (sx < 0)           sx = 0;
            if (sx >= CAM_WIDTH)  sx = CAM_WIDTH - 1;

            uint16_t c = fb[(uint32_t)sy * CAM_WIDTH + (uint32_t)sx];
            int r = (c >> 11) & 0x1F;
            int g = (c >>  5) & 0x3F;
            int b =  c        & 0x1F;

            r = (r << 3) | (r >> 2);
            g = (g << 2) | (g >> 4);
            b = (b << 3) | (b >> 2);

            int32_t idx = (y * PAD_INPUT_W + x) * PAD_INPUT_C;
            pad_input[idx + 0] = pix_lut[r];
            pad_input[idx + 1] = pix_lut[g];
            pad_input[idx + 2] = pix_lut[b];
        }
    }
}

/* 画一帧 + 若干框 */
/* 单缓冲直接绘制（与能出图的版本一致），避免双缓冲切换带来的卡顿 */
static void lcd_draw_frame_with_boxes(const void *p, int32_t xSize, int32_t ySize,
                                      uint32_t argb, int32_t thickness,
                                      pad_box_t *boxes, int32_t box_num,
                                      int32_t fill_ok, uint32_t fill_argb)
{
    if (thickness < 1)
    {
        thickness = 1;
    }

    uint32_t ModeSrc = d2_mode_rgb565;
    d2_device *hdl = d2_handle_obj_get();

    d2_framebuffer(hdl, (uint16_t *)&fb_background[0],
                   LCD_WIDTH, LCD_WIDTH, LCD_HEIGHT, ModeSrc);

    d2_selectrenderbuffer(hdl, d2_renderbuffer_get());
    d2_cliprect(hdl, 0, 0, LCD_WIDTH, LCD_HEIGHT);

    d2_setblitsrc(hdl, (void *)p, xSize, xSize, ySize, ModeSrc);
    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT),
                D2_FIX(0), D2_FIX(0), 0);

    /* 左下角状态方块：红=检测到焊盘，灰=没有 */
    if (fill_ok)
    {
        /* orientation probe: one block at each diagonal corner, 100x100, opaque.
           on the 180-deg flipped panel the framebuffer top-right shows bottom-left. */
        d2_setcolor(hdl, 0, fill_argb);
        d2_renderbox(hdl, D2_FIX(LCD_WIDTH - 110), D2_FIX(10), D2_FIX(100), D2_FIX(100));
        d2_setcolor(hdl, 0, 0xFF0000FFu);
        d2_renderbox(hdl, D2_FIX(10), D2_FIX(LCD_HEIGHT - 110), D2_FIX(100), D2_FIX(100));
    }

    d2_setcolor(hdl, 0, argb);
    d2_width draw_thickness = D2_FIX(thickness);
    d2_u32 flags = d2_le_exclude_none;

    for (int i = 0; i < box_num; i++, boxes++)
    {
        d2_point x1 = D2_FIX(boxes->x1);
        d2_point y1 = D2_FIX(boxes->y1);
        d2_point x2 = D2_FIX(boxes->x2);
        d2_point y2 = D2_FIX(boxes->y2);

        d2_renderline(hdl, x1, y1, x2, y1, draw_thickness, flags);
        d2_renderline(hdl, x1, y1, x1, y2, draw_thickness, flags);
        d2_renderline(hdl, x2, y1, x2, y2, draw_thickness, flags);
        d2_renderline(hdl, x1, y2, x2, y2, draw_thickness, flags);
    }

    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);
    d2_flushframe(hdl);
}

static int cmd_roi(int argc, char **argv)
{
    if (argc >= 2)
    {
        int32_t v = atoi(argv[1]);
        if (v < ROI_SIZE_MIN) v = ROI_SIZE_MIN;
        if (v > ROI_MAX)      v = ROI_MAX;
        roi_size = v;
    }
    if (argc >= 4)
    {
        roi_cx = atoi(argv[2]);
        roi_cy = atoi(argv[3]);
    }
    rt_kprintf("ROI: size=%d  center=(%d,%d)  (frame %dx%d)\n",
               roi_size, roi_cx, roi_cy, CAM_WIDTH, CAM_HEIGHT);
    return 0;
}
MSH_CMD_EXPORT(cmd_roi, set roi: roi <size> [cx cy]);

static int cmd_padstat(int argc, char **argv)
{
    (void)argc; (void)argv;
    rt_kprintf("pad_invoke ret = %d\n", dbg_err);
    rt_kprintf("raw int8: no_pad=%d  pad=%d\n", dbg_defect_q, dbg_good_q);
    rt_kprintf("logits  : no_pad=%.4f pad=%.4f\n", dbg_defect_f, dbg_good_f);
    rt_kprintf("verdict : %s\n", dbg_result == PAD_CLASS_PAD ? "PAD" : "NO_PAD");
    return 0;
}
MSH_CMD_EXPORT(cmd_padstat, print last inference result);

void DisplayVsyncCallback(display_callback_args_t *p_args)
{
    (void)p_args;
}

void hal_entry(void)
{
    LOG_I("========================================================================");
    LOG_I(" Titan Mini: pad presence inspection (Ethos-U55, %dx%d int8)", PAD_INPUT_W, PAD_INPUT_H);
    LOG_I("========================================================================");

    fsp_err_t fsp_status;

    /* ORIENTATION TEST: draw a big letter "F" plus a red corner marker, hold 6 s.
       "F" is asymmetric, so the photo tells us exactly whether the panel is
       rotated 0/90/180/270 or mirrored. Drawn straight into the framebuffer. */
    scr_fill(0x0000);
    scr_rect(100,  80,  70, 320, 0xFFFF);   /* F: vertical stroke */
    scr_rect(170,  80, 240,  70, 0xFFFF);   /* F: top bar        */
    scr_rect(170, 200, 160,  70, 0xFFFF);   /* F: middle bar     */
    scr_rect(LCD_WIDTH - 90, 20, 70, 70, 0xF800);  /* red marker at fb top-right */
    scr_rect(20, LCD_HEIGHT - 90, 70, 70, 0x07E0); /* green marker at fb bottom-left */
    rt_thread_mdelay(6000);

    /* bring-up marker: draw before camera init so a hang is visible on screen */
    scr_fill(0x0320);                                    /* dark green */
    scr_rect(0, 0, LCD_WIDTH, 36, 0xF800);               /* red bar on top */
    scr_rect(0, LCD_HEIGHT - 36, LCD_WIDTH, 36, 0x001F); /* blue bar at bottom */

    build_pix_lut();
    build_disp_lut();

    fsp_status = FSP_ERR_ASSERTION;
    for (int cam_try = 0; cam_try < 3; cam_try++)
    {
        fsp_status = camera_init(false);
        if (FSP_SUCCESS == fsp_status) { break; }
        LOG_E("camera_init fail (try %d) err=%d", cam_try + 1, fsp_status);
        rt_thread_mdelay(300);
    }
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("camera_init gave up, err=%d", fsp_status);
        /* unmistakable red screen with black corner blocks: camera never came up */
        scr_fill(0xF800);
        scr_rect(0, 0, 120, 120, 0x0000);
        scr_rect(LCD_WIDTH - 120, 0, 120, 120, 0x0000);
        scr_rect(0, LCD_HEIGHT - 120, 120, 120, 0x0000);
        scr_rect(LCD_WIDTH - 120, LCD_HEIGHT - 120, 120, 120, 0x0000);
        g_stage = -1;
        return;
    }
    g_stage = 1;

    camera_image_buffer_initialize();

    fsp_status = R_VIN_CaptureStart(&g_cam_vin_ctrl, NULL);
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("R_VIN_CaptureStart fail! err=%d", fsp_status);
        g_stage = -2;
        return;
    }

    g_stage = 2;

    rt_thread_mdelay(100);

    if (RM_ETHOSU_Open(&g_rm_ethosu0_ctrl, &g_rm_ethosu0_cfg) != FSP_SUCCESS)
    {
        LOG_E("Failed to start NPU");
        g_stage = -3;
        return;
    }

    g_stage = 3;

    rt_pin_mode(LED_PIN, PIN_MODE_OUTPUT);
    rt_pin_mode(KEY_PIN, PIN_MODE_INPUT_PULLUP);

    rt_kprintf("[pad] ROI size=%d center=(%d,%d)\n", roi_size, roi_cx, roi_cy);
    rt_kprintf("[pad] use 'roi <size> [cx cy]' to adjust, 'padstat' to dump result\n");

    uint32_t frames = 0;
    int32_t  good_cnt = 0;

    while (1)
    {
        if (!camera_capture_post_process())
        {
            rt_thread_mdelay(1);
            continue;
        }

        uint16_t *frame = (uint16_t *)camera_data_ready_buffer_pointer_get();
        if (!frame)
        {
            rt_thread_mdelay(1);
            continue;
        }

        g_stage = 4;
        g_frames = frames + 1;

        frame_to_input(frame);
        frame_rotate_brighten(frame, g_rot);

        dbg_err = pad_invoke();

        dbg_defect_q = pad_output[PAD_CLASS_NOPAD];
        dbg_good_q   = pad_output[PAD_CLASS_PAD];
        dbg_defect_f = ((float)dbg_defect_q - PAD_OUTPUT_ZP) * PAD_OUTPUT_SCALE;
        dbg_good_f   = ((float)dbg_good_q   - PAD_OUTPUT_ZP) * PAD_OUTPUT_SCALE;
        dbg_result   = (dbg_good_f > dbg_defect_f) ? PAD_CLASS_PAD : PAD_CLASS_NOPAD;

        int is_pad = (dbg_result == PAD_CLASS_PAD);
        good_cnt += is_pad;

        /* ROI 在屏幕上的位置（640x480 -> LCD_WIDTH x LCD_HEIGHT） */
        int32_t half = roi_size / 2;
        pad_box_t box;
        int32_t bx1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        int32_t by1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        int32_t bx2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        int32_t by2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x1 = LCD_WIDTH  - bx2;
        box.y1 = LCD_HEIGHT - by2;
        box.x2 = LCD_WIDTH  - bx1;
        box.y2 = LCD_HEIGHT - by1;

        uint32_t roi_argb = 0xFFE0E0E0u;                                  /* ROI 细白框，便于对准 */
        uint32_t sq_argb  = is_pad ? 0xFFFF0000u : 0xFF808080u;            /* 红=焊盘，灰=无 */
        lcd_draw_frame_with_boxes(g_rot, CAM_WIDTH, CAM_HEIGHT,
                                  roi_argb, 2, &box, 1,
                                  1, sq_argb);

        frames++;
        if ((frames % 30) == 0)
        {
            rt_kprintf("[pad] frame=%u  ok=%d/%u  last=%s  logit(defect=%.3f good=%.3f) ret=%d\n",
                       frames, good_cnt, frames,
                       is_pad ? "PAD" : "NO_PAD",
                       (double)dbg_defect_f, (double)dbg_good_f, dbg_err);
        }

        rt_pin_write(LED_PIN, is_pad ? PIN_HIGH : PIN_LOW);

        rt_thread_mdelay(5);
    }
}
