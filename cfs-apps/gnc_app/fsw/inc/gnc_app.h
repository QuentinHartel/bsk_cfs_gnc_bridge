#ifndef GNC_APP_H
#define GNC_APP_H

#include "cfe.h"

#define GNC_APP_PIPE_DEPTH 32

typedef struct
{
    CFE_SB_PipeId_t CommandPipe;
    CFE_ES_TaskId_t TaskId;
} GNC_AppData_t;

void GNC_AppMain(void);
int32 GNC_AppInit(void);
void  GNC_ProcessCommandPacket(void);

#endif
