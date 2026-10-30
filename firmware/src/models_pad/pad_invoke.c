#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "pad_invoke.h"
#include "pad_tensors.h"
#include "pad_command_stream.h"
#include "pad_model_data.h"

#include "common_data.h"
#include "ethosu_driver.h"

__attribute__((aligned(16))) uint8_t pad_arena[PAD_ARENA_BYTES];
__attribute__((aligned(16))) int8_t  pad_input[PAD_INPUT_BYTES];
__attribute__((aligned(16))) int8_t  pad_output[PAD_OUTPUT_BYTES];

/* region0=权重 region1=arena region2=fast scratch region3=输入 region4=输出 */
int pad_invoke(void)
{
    uint64_t base_addrs[5];
    size_t   base_addrs_size[5];

    base_addrs[0]      = (uint64_t)(uintptr_t)pad_model_data;
    base_addrs_size[0] = pad_model_data_size;
    base_addrs[1]      = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[1] = PAD_ARENA_BYTES;
    base_addrs[2]      = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[2] = PAD_ARENA_BYTES;
    base_addrs[3]      = (uint64_t)(uintptr_t)pad_input;
    base_addrs_size[3] = PAD_INPUT_BYTES;
    base_addrs[4]      = (uint64_t)(uintptr_t)pad_output;
    base_addrs_size[4] = PAD_OUTPUT_BYTES;

    memset(pad_output, 0, PAD_OUTPUT_BYTES);

    return ethosu_invoke_v3(&g_ethosu0, (uint8_t *)pad_cms, (int)pad_cms_size,
                            base_addrs, base_addrs_size, 5, NULL);
}
