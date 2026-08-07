/**
 * @file mcu_debug.c
 * @brief MCU Debug Assistant 客户端 SDK 实现
 */
#include "mcu_debug.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define DEBUG_BUFFER_SIZE 256

static char s_tx_buffer[DEBUG_BUFFER_SIZE];

/* 弱定义：用户工程未实现 Debug_UART_Send 时为空操作，保证链接不失败 */
__attribute__((weak)) void Debug_UART_Send(const uint8_t *data, uint16_t len)
{
    (void)data;
    (void)len;
}

void Debug_Init(void)
{
    /* 预留：需要时可在此初始化 DMA 发送等 */
}

void Debug_Print(const char *msg)
{
    if (msg == NULL) {
        return;
    }
    Debug_Printf("%s", msg);
}

void Debug_Printf(const char *fmt, ...)
{
    va_list args;
    int len;

    if (fmt == NULL) {
        return;
    }

    va_start(args, fmt);
    len = vsnprintf(s_tx_buffer, sizeof(s_tx_buffer), fmt, args);
    va_end(args);

    if (len < 0) {
        return;
    }
    if (len >= (int)sizeof(s_tx_buffer)) {
        len = (int)sizeof(s_tx_buffer) - 1; /* 截断超长消息 */
    }

    Debug_UART_Send((const uint8_t *)s_tx_buffer, (uint16_t)len);
    Debug_UART_Send((const uint8_t *)"\r\n", 2);
}
