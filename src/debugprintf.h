#pragma once

#define DEBUG_PRINT

#ifdef DEBUG_PRINT
#define debugprintf(...) printf(__VA_ARGS__)
#else
#define debugprintf(...)
#endif
