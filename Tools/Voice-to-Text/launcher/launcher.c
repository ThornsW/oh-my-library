/*
 * Single-file launcher for Voice-to-Text.
 *
 * build.sh appends the Python code (a zip archive) to this compiled program.
 * At start we hand our own file to the system Python, which runs the zip's
 * __main__.py; data in front of a zip archive is allowed by the zip format.
 */
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char self[PATH_MAX];
    ssize_t n = readlink("/proc/self/exe", self, sizeof self - 1);
    if (n < 0) {
        perror("voice-to-text: cannot find own path");
        return 1;
    }
    self[n] = '\0';

    const char *python = getenv("VTT_PYTHON");
    if (python == NULL || *python == '\0')
        python = "/usr/bin/python3";

    char **args = calloc((size_t)argc + 3, sizeof *args);
    if (args == NULL)
        return 1;
    int i = 0;
    args[i++] = (char *)python;
    args[i++] = "-B"; /* never write __pycache__ */
    args[i++] = self;
    for (int k = 1; k < argc; k++)
        args[i++] = argv[k];
    args[i] = NULL;

    execv(python, args);
    fprintf(stderr, "voice-to-text: cannot start %s (set VTT_PYTHON): ", python);
    perror(NULL);
    return 127;
}
