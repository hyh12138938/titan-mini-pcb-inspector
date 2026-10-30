#ifndef PAD_INVOKE_H
#define PAD_INVOKE_H
#include <stdint.h>
#include "pad_tensors.h"
extern uint8_t pad_arena[PAD_ARENA_BYTES];
extern int8_t  pad_input[PAD_INPUT_BYTES];
extern int8_t  pad_output[PAD_OUTPUT_BYTES];
int pad_invoke(void);
#endif
