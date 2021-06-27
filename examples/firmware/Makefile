include ../include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

CFLAGS += -ffreestanding -flto -nostartfiles -fomit-frame-pointer -Wl,--gc-section --specs=nano.specs
CFLAGS += -I$(FIRMWARE_DIRECTORY)/
CFLAGS += -Wno-missing-prototypes

# TinyUSB common
SOURCES += $(addprefix tinyusb/src/, \
	common/tusb_fifo.c \
	class/msc/msc_device.c \
	class/midi/midi_device.c \
	class/cdc/cdc_device.c \
	class/hid/hid_device.c \
	class/dfu/dfu_rt_device.c \
	device/usbd.c \
	device/usbd_control.c \
	tusb.c \
)
CFLAGS += -Itinyusb/src

# TinyUSB driver
NO2USB_PATH = $(FIRMWARE_DIRECTORY)/../../src/no2migen/cores/no2usb/fw/tinyusb/
HEADERS += dcd_no2usb_hw.h
SOURCES += dcd_no2usb.c

# TinyUSB custom
HEADERS += $(addprefix $(FIRMWARE_DIRECTORY)/, \
	tusb_config.h \
	dcd_no2usb_config.h \
)

SOURCES += $(addprefix $(FIRMWARE_DIRECTORY)/, \
	msc_disk.c \
	usb_descriptors.c \
)

# App
HEADERS += $(addprefix $(FIRMWARE_DIRECTORY)/, \
	console.h \
	mini-printf.h \
)

SOURCES += $(addprefix $(FIRMWARE_DIRECTORY)/, \
	start.S \
	console.c \
	mini-printf.c  \
	firmware.c \
)

# Targets
all: tinyusb firmware.bin

firmware.elf: $(FIRMWARE_DIRECTORY)/lnk-app.lds $(HEADERS) $(SOURCES)
	$(CC) $(CFLAGS) -Wl,-Bstatic,-L,$(BUILDINC_DIRECTORY)/generated,-T,$(FIRMWARE_DIRECTORY)/lnk-app.lds,--strip-debug -o $@ $(SOURCES)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

dcd_no2usb_hw.h: $(NO2USB_PATH)/dcd_no2usb_hw.h
	cp $< $@

dcd_no2usb.c: $(NO2USB_PATH)/dcd_no2usb.c
	cp $< $@

tinyusb:
	git clone https://github.com/hathach/tinyusb.git

clean:
	rm -f *.bin *.elf *.o *.gen.h

.PHONY: clean
