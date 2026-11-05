/* Restart the console, enter rest mode or turn it off. Built once per action by scripts/build-power.sh, and sent to
 * elfldr by the `power` tool. It prints the outcome to elfldr's log; the caller watches for the console going away.
 */
#include <stdio.h>
#include <stddef.h>
#include <string.h>

#ifndef POWER_ACTION
#error "build with -DPOWER_ACTION=\"restart\", \"standby\" or \"off\""
#endif

int sceKernelLoadStartModule(const char *path, size_t argc, const void *argv, unsigned flags, void *opt, int *result);
int sceKernelDlsym(int module, const char *name, void **address);

static const char *const MODULES[] = {
    "/system/common/lib/libSceSystemStateMgr.sprx",
    "/system/priv/lib/libSceSystemStateMgr.sprx",
};

int main(void) {
    const char *symbol = strcmp(POWER_ACTION, "restart") == 0   ? "sceSystemStateMgrReboot"
                         : strcmp(POWER_ACTION, "standby") == 0 ? "sceSystemStateMgrEnterStandby"
                                                                : "sceSystemStateMgrTurnOff";
    for (size_t i = 0; i < sizeof(MODULES) / sizeof(MODULES[0]); i++) {
        int module = sceKernelLoadStartModule(MODULES[i], 0, NULL, 0, NULL, NULL);
        void *address = NULL;
        if (module < 0) {
            printf("ps5power: %s: 0x%08x\n", MODULES[i], (unsigned)module);
            continue;
        }
        int rc = sceKernelDlsym(module, symbol, &address);
        if (rc != 0 || address == NULL) {
            printf("ps5power: no %s in %s: 0x%08x\n", symbol, MODULES[i], (unsigned)rc);
            continue;
        }
        rc = ((int (*)(void))address)();
        printf("ps5power: %s returned 0x%08x\n", symbol, (unsigned)rc);
        return rc;
    }
    return 1;
}
