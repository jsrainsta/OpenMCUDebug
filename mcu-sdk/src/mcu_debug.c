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

/* ======================== Stage 2 实现 ======================== */

void Debug_Device_Init(const char *name, const char *version)
{
    if (name == NULL) {
        return;
    }
    if (version && version[0] != '\0') {
        Debug_Printf("$DEV name=%s,ver=%s", name, version);
    } else {
        Debug_Printf("$DEV name=%s,ver=0", name);
    }
}

void Debug_Register_Channel(uint8_t id, const char *name,
                            const char *type, const char *unit,
                            const char *visual)
{
    if (name == NULL || type == NULL) {
        return;
    }
    /* visual 为 NULL / 空 / text 时省略该字段，保持与旧协议完全兼容 */
    int has_visual = (visual != NULL) && (visual[0] != '\0')
                     && (strcmp(visual, DBG_VISUAL_TEXT) != 0);

    if (unit && unit[0] != '\0') {
        if (has_visual) {
            Debug_Printf("$CH id=%u,name=%s,type=%s,unit=%s,visual=%s",
                         id, name, type, unit, visual);
        } else {
            Debug_Printf("$CH id=%u,name=%s,type=%s,unit=%s",
                         id, name, type, unit);
        }
    } else if (has_visual) {
        Debug_Printf("$CH id=%u,name=%s,type=%s,visual=%s",
                     id, name, type, visual);
    } else {
        Debug_Printf("$CH id=%u,name=%s,type=%s", id, name, type);
    }
}

void Debug_Send_Val(uint8_t id, int32_t value)
{
    Debug_Printf("$VAL id=%u,val=%ld", id, (long)value);
}

void Debug_Send_Val_Float(uint8_t id, float value)
{
    /* 缓冲区足够容纳 $VAL id=255,val=-1.234567e+38\r\n 等极端格式 */
    Debug_Printf("$VAL id=%u,val=%.6g", id, (double)value);
}

void Debug_Send_Val_Str(uint8_t id, const char *value)
{
    if (value == NULL) {
        return;
    }
    Debug_Printf("$VAL id=%u,val=%s", id, value);
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
