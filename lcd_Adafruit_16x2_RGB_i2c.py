import machine
import time
from micropython import const

# --- CONSTANTES MCP23017 ---
_MCP_ADDR = const(0x20)
_IODIRA = const(0x00) # Direction Port A
_IODIRB = const(0x01) # Direction Port B
_GPIOA  = const(0x12) # Valeur Port A
_GPIOB  = const(0x13) # Valeur Port B
_GPPUA  = const(0x0C) # Pull-up Port A
_GPPUB  = const(0x0D) # Pull-up Port B

# --- CONSTANTES LCD (Déplacées ici pour éviter l'AttributeError) ---
_LCD_CLEARDISPLAY = const(0x01)
_LCD_RETURNHOME = const(0x02)
_LCD_ENTRYMODESET = const(0x04)
_LCD_DISPLAYCONTROL = const(0x08)
_LCD_CURSORSHIFT = const(0x10)
_LCD_FUNCTIONSET = const(0x20)
_LCD_SETDDRAMADDR = const(0x80)

# Flags LCD
_LCD_DISPLAYON = const(0x04)
_LCD_CURSORON = const(0x02)
_LCD_BLINKON = const(0x01)
_LCD_ENTRYLEFT = const(0x02)
_LCD_ENTRYSHIFTDECREMENT = const(0x00)
_LCD_4BITMODE = const(0x00)
_LCD_2LINE = const(0x08)
_LCD_5X8DOTS = const(0x00)

# --- CLASSE PILOTE MCP23017 ---
class MCP23017:
    def __init__(self, i2c, address=_MCP_ADDR):
        self.i2c = i2c
        self.address = address
        # Initialisation: Mettre tous les pins en entrée par sécurité
        try:
            self._write_reg(_IODIRA, 0xFF)
            self._write_reg(_IODIRB, 0xFF)
            # Désactiver les pull-ups
            self._write_reg(_GPPUA, 0x00)
            self._write_reg(_GPPUB, 0x00)
            
            # Cache pour les registres de sortie
            self._gpioa = 0x00
            self._gpiob = 0x00
            self._write_reg(_GPIOA, self._gpioa)
            self._write_reg(_GPIOB, self._gpiob)
        except OSError:
            print("Erreur: Impossible de communiquer avec le MCP23017. Vérifiez le câblage.")
            raise

    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    def _read_reg(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def pin_mode(self, pin, mode, pullup=False):
        # mode: 'IN' ou 'OUT'
        reg_dir = _IODIRA if pin < 8 else _IODIRB
        reg_gpu = _GPPUA if pin < 8 else _GPPUB
        bit = pin % 8
        
        current_dir = self._read_reg(reg_dir)
        current_gpu = self._read_reg(reg_gpu)

        if mode == 'IN':
            current_dir |= (1 << bit)
            if pullup:
                current_gpu |= (1 << bit)
            else:
                current_gpu &= ~(1 << bit)
        else: # OUT
            current_dir &= ~(1 << bit)
            current_gpu &= ~(1 << bit) 

        self._write_reg(reg_dir, current_dir)
        self._write_reg(reg_gpu, current_gpu)

    def digital_write(self, pin, value):
        bit = pin % 8
        if pin < 8:
            if value:
                self._gpioa |= (1 << bit)
            else:
                self._gpioa &= ~(1 << bit)
            self._write_reg(_GPIOA, self._gpioa)
        else:
            if value:
                self._gpiob |= (1 << bit)
            else:
                self._gpiob &= ~(1 << bit)
            self._write_reg(_GPIOB, self._gpiob)

    def digital_read(self, pin):
        reg = _GPIOA if pin < 8 else _GPIOB
        bit = pin % 8
        val = self._read_reg(reg)
        return (val >> bit) & 1

# --- CLASSE ECRAN LCD RGB ADAFRUIT ---
class Adafruit_RGB_LCD:
    # Mapping des Pins Adafruit Shield
    BUTTON_SELECT = 0
    BUTTON_RIGHT  = 1
    BUTTON_DOWN   = 2
    BUTTON_UP     = 3
    BUTTON_LEFT   = 4
    
    LED_RED   = 6 # Port A
    LED_GREEN = 7 # Port A
    LED_BLUE  = 8 # Port B (bit 0)

    # Bits Port B pour LCD
    LCD_RS_BIT = 7
    LCD_E_BIT  = 5
    LCD_D4_BIT = 4
    LCD_D5_BIT = 3
    LCD_D6_BIT = 2
    LCD_D7_BIT = 1

    def __init__(self, mcp, cols=16, lines=2):
        self.mcp = mcp
        self.cols = cols
        self.lines = lines
        
        # Configuration des Pins
        for p in range(5):
            self.mcp.pin_mode(p, 'IN', pullup=True)
            
        self.mcp.pin_mode(self.LED_RED, 'OUT')
        self.mcp.pin_mode(self.LED_GREEN, 'OUT')
        self.mcp.pin_mode(self.LED_BLUE, 'OUT')
        
        for p in range(9, 16):
            self.mcp.pin_mode(p, 'OUT')

        # Initialisation séquence LCD
        self._displayfunction = _LCD_4BITMODE | _LCD_2LINE | _LCD_5X8DOTS
        self._displaycontrol = _LCD_DISPLAYON 
        self._displaymode = _LCD_ENTRYLEFT | _LCD_ENTRYSHIFTDECREMENT

        time.sleep_ms(50)
        self._write4bits(0x03)
        time.sleep_ms(5)
        self._write4bits(0x03)
        time.sleep_ms(5)
        self._write4bits(0x03)
        time.sleep_ms(1)
        self._write4bits(0x02) 

        self.send(_LCD_FUNCTIONSET | self._displayfunction, False)
        self.send(_LCD_DISPLAYCONTROL | self._displaycontrol, False)
        self.clear()
        self.send(_LCD_ENTRYMODESET | self._displaymode, False)
        
        self.set_color([0, 0, 0])

    def _write4bits(self, value):
        current_gpiob = self.mcp._gpiob 
        mask = ~( (1<<self.LCD_D4_BIT) | (1<<self.LCD_D5_BIT) | 
                  (1<<self.LCD_D6_BIT) | (1<<self.LCD_D7_BIT) | (1<<self.LCD_E_BIT) )
        new_gpiob = current_gpiob & mask
        
        if (value >> 0) & 0x01: new_gpiob |= (1 << self.LCD_D4_BIT)
        if (value >> 1) & 0x01: new_gpiob |= (1 << self.LCD_D5_BIT)
        if (value >> 2) & 0x01: new_gpiob |= (1 << self.LCD_D6_BIT)
        if (value >> 3) & 0x01: new_gpiob |= (1 << self.LCD_D7_BIT)
        
        self.mcp._gpiob = new_gpiob
        self.mcp._write_reg(_GPIOB, new_gpiob)
        
        # Pulse Enable
        self.mcp._gpiob |= (1 << self.LCD_E_BIT)
        self.mcp._write_reg(_GPIOB, self.mcp._gpiob)
        time.sleep_us(1)
        self.mcp._gpiob &= ~(1 << self.LCD_E_BIT)
        self.mcp._write_reg(_GPIOB, self.mcp._gpiob)
        time.sleep_us(100)

    def send(self, value, mode):
        # mode: False=Command, True=Data
        if mode:
            self.mcp._gpiob |= (1 << self.LCD_RS_BIT)
        else:
            self.mcp._gpiob &= ~(1 << self.LCD_RS_BIT)
        self.mcp._write_reg(_GPIOB, self.mcp._gpiob)
        
        self._write4bits(value >> 4) 
        self._write4bits(value & 0x0F) 

    def clear(self):
        # Utilisation de la constante globale directement
        self.send(_LCD_CLEARDISPLAY, False)
        time.sleep_ms(2)

    def home(self):
        self.send(_LCD_RETURNHOME, False)
        time.sleep_ms(2)

    def set_cursor(self, col, row):
        offsets = [0x00, 0x40, 0x14, 0x54]
        if row > self.lines - 1: row = self.lines - 1
        self.send(_LCD_SETDDRAMADDR | (col + offsets[row]), False)

    def message(self, text):
        line = 0
        col = 0
        for char in text:
            if char == '\n':
                line += 1
                col = 0
                self.set_cursor(col, line)
            else:
                self.send(ord(char), True)
                col += 1

    def set_color(self, rgb):
        r = 0 if rgb[0] > 0 else 1
        g = 0 if rgb[1] > 0 else 1
        b = 0 if rgb[2] > 0 else 1
        
        self.mcp.digital_write(self.LED_RED, r)
        self.mcp.digital_write(self.LED_GREEN, g)
        self.mcp.digital_write(self.LED_BLUE, b)

    def show_cursor(self, show):
        if show:
            self._displaycontrol |= _LCD_CURSORON
        else:
            self._displaycontrol &= ~_LCD_CURSORON
        self.send(_LCD_DISPLAYCONTROL | self._displaycontrol, False)

    def blink_cursor(self, blink):
        if blink:
            self._displaycontrol |= _LCD_BLINKON
        else:
            self._displaycontrol &= ~_LCD_BLINKON
        self.send(_LCD_DISPLAYCONTROL | self._displaycontrol, False)

    def move_left(self):
        self.send(_LCD_CURSORSHIFT | 0x08 | 0x00, False)

    def move_right(self):
        self.send(_LCD_CURSORSHIFT | 0x08 | 0x04, False)
        
    def text_direction_rtl(self):
        self._displaymode &= ~_LCD_ENTRYLEFT
        self.send(_LCD_ENTRYMODESET | self._displaymode, False)

    def text_direction_ltr(self):
        self._displaymode |= _LCD_ENTRYLEFT
        self.send(_LCD_ENTRYMODESET | self._displaymode, False)

    @property
    def left_button(self): return not self.mcp.digital_read(self.BUTTON_LEFT)
    @property
    def right_button(self): return not self.mcp.digital_read(self.BUTTON_RIGHT)
    @property
    def up_button(self): return not self.mcp.digital_read(self.BUTTON_UP)
    @property
    def down_button(self): return not self.mcp.digital_read(self.BUTTON_DOWN)
    @property
    def select_button(self): return not self.mcp.digital_read(self.BUTTON_SELECT)
    @property
    def all_buttons(self): return 0x1F ^ (self.mcp._read_reg(_GPIOA) & 0x1F) # mask to return only the 5 bits and inverse them

