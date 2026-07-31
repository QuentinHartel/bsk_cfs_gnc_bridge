#include "gnc_app.h"
#include "gnc_app_events.h"
#include "cfe.h"

GNC_AppData_t GNC_AppData;

void GNC_APP_AppMain(void)
{
    int32  status;
    uint32 RunStatus = CFE_ES_RunStatus_APP_RUN;

    CFE_ES_PerfLogEntry(0);

    status = GNC_AppInit();
    if (status != CFE_SUCCESS)
    {
        RunStatus = CFE_ES_RunStatus_APP_ERROR;
    }

    while (CFE_ES_RunLoop(&RunStatus) == true)
    {
        CFE_ES_PerfLogExit(0);

        /* Idle loop — this is where sensor/actuator message handling
           (and eventually your Basilisk bridge messages) will go */
        OS_TaskDelay(1000);

        CFE_ES_PerfLogEntry(0);
    }

    CFE_ES_PerfLogExit(0);
    CFE_ES_ExitApp(RunStatus);
}

int32 GNC_AppInit(void)
{
    int32 status;

    memset(&GNC_AppData, 0, sizeof(GNC_AppData));

    // App registration done automatically in newer versions of cFS
    
    status = CFE_EVS_Register(NULL, 0, CFE_EVS_EventFilter_BINARY);
    if (status != CFE_SUCCESS)
    {
	return status;
    }


    status = CFE_SB_CreatePipe(&GNC_AppData.CommandPipe,
                                GNC_APP_PIPE_DEPTH,
                                "GNC_APP_CMD_PIPE");
    if (status != CFE_SUCCESS)
    {
        return status;
    }

    CFE_EVS_SendEvent(GNC_APP_INIT_INF_EID, CFE_EVS_EventType_INFORMATION,
		    		"GNC_APP: Initialized successfully");

    return CFE_SUCCESS;
}
