/* Print the real free space of the console's drives as one line of JSON, then exit. Playden's own number can be far
 * off on a nearly full disk. Sent to elfldr by the `disk` tool, which reads the output back from the same connection.
 */
#include <stdio.h>
#include <sys/mount.h>
#include <sys/param.h>

static const char *const PATHS[] = {"/data", "/user", "/system_data", "/mnt/usb0", "/mnt/ext0"};

int main(void) {
    int first = 1;
    printf("{");
    for (size_t i = 0; i < sizeof(PATHS) / sizeof(PATHS[0]); i++) {
        struct statfs info;
        if (statfs(PATHS[i], &info) != 0) {
            continue;
        }
        printf("%s\"%s\":{\"bytes\":%llu,\"free\":%llu,\"available\":%lld,\"device\":\"%s\"}", first ? "" : ",",
               PATHS[i], (unsigned long long)info.f_blocks * info.f_bsize,
               (unsigned long long)info.f_bfree * info.f_bsize, (long long)info.f_bavail * (long long)info.f_bsize,
               info.f_mntfromname);
        first = 0;
    }
    printf("}\n");
    fflush(stdout);
    return 0;
}
