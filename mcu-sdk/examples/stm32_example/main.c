/**
 * @file main.c
 * @brief STM32 使用示例（配合 STM32CubeMX 生成的 HAL 工程）
 *
 * 集成步骤：
 * 1. 把 mcu-sdk/include 和 mcu-sdk/src 加入工程编译
 * 2. 在工程中实现 Debug_UART_Send（见下方示例），换成你自己的串口句柄
 * 3. 启动单字节中断接收（见 main()），在 HAL_UART_RxCpltCallback 中处理命令
 * 4. 用 MCU Debug Assistant 连接，波特率保持一致（示例默认 115200）
 */
#include "mcu_debug.h"
#include "main.h" /* CubeMX 生成 */
#include <string.h>

extern UART_HandleTypeDef huart1;

/* 底层串口发送：把调试输出交给 HAL */
void Debug_UART_Send(const uint8_t *data, uint16_t len)
{
    HAL_UART_Transmit(&huart1, data, len, 100);
}

/* ---------------- 命令接收（单字节中断 + 行缓冲） ---------------- */

static uint8_t s_rx_byte;
static char s_rx_line[64];
static uint16_t s_rx_len = 0;

static void handle_command(const char *cmd)
{
    if (strcmp(cmd, "led on") == 0) {
        HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_SET);
        Debug_Info("LED ON");
    } else if (strcmp(cmd, "led off") == 0) {
        HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_RESET);
        Debug_Info("LED OFF");
    } else {
        Debug_Error("Unknown command: %s", cmd);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART1) {
        return;
    }

    if (s_rx_byte == '\n' || s_rx_len >= sizeof(s_rx_line) - 1) {
        s_rx_line[s_rx_len] = '\0';
        /* 去掉行尾可能存在的 \r（PC 端默认行尾是 CRLF） */
        if (s_rx_len > 0 && s_rx_line[s_rx_len - 1] == '\r') {
            s_rx_line[s_rx_len - 1] = '\0';
        }
        if (s_rx_len > 0) {
            handle_command(s_rx_line);
        }
        s_rx_len = 0;
    } else {
        s_rx_line[s_rx_len++] = (char)s_rx_byte;
    }

    HAL_UART_Receive_IT(&huart1, &s_rx_byte, 1);
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();

    Debug_Init();
    Debug_Info("System Start");
    Debug_Data("Temperature=%d", 25);

    /* 启动单字节中断接收 */
    HAL_UART_Receive_IT(&huart1, &s_rx_byte, 1);

    while (1) {
        /* 主循环：业务逻辑 */
    }
}
