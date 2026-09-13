/* Includes */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/times.h>
#include <time.h>

/* Functions */
void initialise_monitor_handles() {}

/* Syscalls (stub implementations to avoid compile warnings and possibe future problems) */
int _getpid(void) { return 1; }

off_t   _lseek(int fd, off_t ptr, int dir) { return -1; }
ssize_t _read(int fd, void *ptr, size_t len) { return -1; }
ssize_t _write(int fd, const void *ptr, size_t len) { return -1; }
int     _close(int fd) { return -1; }
