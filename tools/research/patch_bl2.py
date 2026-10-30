import re
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\HAL_Drivers\drv_lcd.c"
NEW = """static void turn_on_lcd_backlight(void)
{
    /* Panel BL is level-enabled: drive it high for max brightness.
       This board's FSP has no PWM instance registered (rt_device_find("pwm7")
       returns NULL), so drive the BL pin as GPIO to guarantee backlight on. */
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
    rt_pin_mode(LCD_BL_PIN, PIN_MODE_OUTPUT);
    rt_pin_write(LCD_BL_PIN, PIN_HIGH);
}"""
raw = open(P, "rb").read()
m = re.search(rb"static void turn_on_lcd_backlight\(void\)\s*\{.*?\n\}", raw, re.S)
if not m:
    print("NOT FOUND"); raise SystemExit(1)
out = raw[:m.start()] + NEW.encode("ascii") + raw[m.end():]
open(P, "wb").write(out)
print("OK, bytes:", len(out))
