# -*- coding: utf-8 -*-
"""把 drv_lcd.c 的 turn_on_lcd_backlight 改成：无论 PWM 是否可用，都把 BL 引脚拉高"""
import re
import sys

PATH = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\HAL_Drivers\drv_lcd.c"

NEW = """static void turn_on_lcd_backlight(void)
{
    /* 面板 BL 为电平使能：拉高即最亮。
       本板 FSP 里并没有 PWM 实例（rt_device_find("pwm7") 返回 NULL），
       所以这里以 GPIO 直接驱动，保证背光一定亮。 */
#ifdef BSP_USING_LCD_PWM_BACKLIGHT
    {
        struct rt_device_pwm *pwm_dev =
            (struct rt_device_pwm *)rt_device_find(LCD_PWM_DEV_NAME);
        if (pwm_dev != RT_NULL)
        {
            rt_pwm_set(pwm_dev, 0, 10000, 5000);
            rt_pwm_enable(pwm_dev, 0);
        }
    }
#endif
    rt_pin_mode(LCD_BL_PIN, PIN_MODE_OUTPUT);   /* LCD_BL */
    rt_pin_write(LCD_BL_PIN, PIN_HIGH);
}"""


def main():
    with open(PATH, "r", encoding="utf-8", errors="surrogateescape") as f:
        src = f.read()

    m = re.search(r"static void turn_on_lcd_backlight\(void\)\s*\{.*?\n\}", src, re.S)
    if not m:
        print("!! 没找到函数")
        return 1
    print("原实现（前 3 行）:")
    for line in src[m.start():m.start() + 200].splitlines()[:4]:
        print("   ", line)

    out = src[:m.start()] + NEW + src[m.end():]
    with open(PATH, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(out)
    print("已替换")
    return 0


if __name__ == "__main__":
    sys.exit(main())
