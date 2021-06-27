INCLUDE output_format.ld
INCLUDE regions.ld

ENTRY(_start)
SECTIONS {
    __stacktop = ORIGIN(sram) + LENGTH(sram);
    .text :
    {
        . = ALIGN(4);
        *(.text.start)
        . = ALIGN(4);
        _etext = .;
        _sidata = _etext;
    } >rom
    .data : AT ( _sidata )
    {
        . = ALIGN(4);
        _sdata = .;
        _ram_start = .;
        . = ALIGN(4);

        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        *(.srodata)
        *(.srodata*)

        *(.data)
        *(.data*)
        *(.sdata)
        *(.sdata*)
        . = ALIGN(4);
        _edata = .;
    } >sram
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(.sbss)
        *(.sbss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } >sram
    .heap :
    {
        . = ALIGN(4);
        _heap_start = .;
    } >sram
}
