.syntax unified
.cpu cortex-m0
.thumb

.global __StackTop
.global Reset_Handler

.section .isr_vector,"a",%progbits
.type g_pfnVectors, %object

g_pfnVectors:
    .word __StackTop
    .word Reset_Handler
    .word NMI_Handler
    .word HardFault_Handler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word SVC_Handler
    .word 0
    .word 0
    .word PendSV_Handler
    .word SysTick_Handler

    /* Placeholder IRQs */
    .rept 48
    .word Default_Handler
    .endr

.section .text.Reset_Handler
Reset_Handler:
    ldr r0, =__sidata
    ldr r1, =__sdata
    ldr r2, =__edata
1:
    cmp r1, r2
    bcc 2f
    b 3f
2:
    ldr r3, [r0], #4
    str r3, [r1], #4
    b 1b
3:
    ldr r0, =__sbss
    ldr r1, =__ebss
    movs r2, #0
4:
    cmp r0, r1
    bcc 5f
    b 6f
5:
    str r2, [r0], #4
    b 4b
6:
    bl SystemInit
    bl main
    b .

.section .text.Default_Handler,"ax",%progbits
Default_Handler:
    b .

.weak NMI_Handler
.set NMI_Handler, Default_Handler
.weak HardFault_Handler
.set HardFault_Handler, Default_Handler
.weak SVC_Handler
.set SVC_Handler, Default_Handler
.weak PendSV_Handler
.set PendSV_Handler, Default_Handler
.weak SysTick_Handler
.set SysTick_Handler, Default_Handler
