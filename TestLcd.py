# Test of Adafruit RGB Positive 16x2 LCD+Keypad Kit for Raspberry Pi
# Product ID: 1109
# connected to raspberry pi pico w
# in MicroPython

import machine, time
from lcd_Adafruit_16x2_RGB_i2c import MCP23017, Adafruit_RGB_LCD

def test():
    print("Démarrage du test LCD...")
    
    # I2C sur GP2/GP3 (Pico W I2C1)
    i2c = machine.I2C(1, sda=machine.Pin(2), scl=machine.Pin(3), freq=400000)

    devices = i2c.scan()
    print("Appareils I2C trouvés:", [hex(d) for d in devices])
    if 0x20 not in devices:
        print("ERREUR: MCP23017 (0x20) non trouvé!")
        return

    try:
        mcp = MCP23017(i2c)
        lcd = Adafruit_RGB_LCD(mcp)
    except Exception as e:
        print("Erreur init:", e)
        return

    lcd.clear()
    
    print("Test Couleurs...")
    lcd.set_color([100, 0, 0])
    time.sleep(0.5)
    
    lcd.message("Hello\nMicroPython")
    time.sleep(1)
    
    lcd.set_color([0, 100, 0])
    time.sleep(0.5)
    
    lcd.set_color([0, 0, 100])
    time.sleep(0.5)
    
    lcd.set_color([100, 100, 100])
    lcd.clear()

    print("Test Boutons... (Appuyez sur les boutons)")
    lcd.message("Test Boutons...")
    
    last_msg = ""
    
    while True:
        msg = ""
        if lcd.left_button: msg = "Gauche"
        elif lcd.right_button: msg = "Droite"
        elif lcd.up_button: msg = "Haut"
        elif lcd.down_button: msg = "Bas"
        elif lcd.select_button: msg = "Select"
        
        if msg and msg != last_msg:
            lcd.clear()
            lcd.message(msg)
            print("Bouton:", msg)
            last_msg = msg
            if msg == "Select": # Quitter la boucle si select
                break
        time.sleep(0.1)

    lcd.clear()
    lcd.set_color([0,0,0])
    scroll_msg = "Fin du test"
    lcd.message(scroll_msg)
    time.sleep(2)
    for i in range(len(scroll_msg)):
        time.sleep(0.5)
        lcd.move_left()
    lcd.message("Bye..")
    time.sleep(1)
    lcd.clear()
    

test()
