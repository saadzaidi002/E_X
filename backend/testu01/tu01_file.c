/*
 * tu01_file: run an official TestU01 battery on a raw binary file and print
 * one machine-readable line per test.
 *
 *   tu01_file rabbit     <file> <nbits>
 *   tu01_file alphabit   <file> <nbits>
 *   tu01_file smallcrush <file>
 *
 * Output lines:
 *   P\t<test name>\t<p-value>
 *   WORDS_USED\t<32-bit words read>        (smallcrush only)
 *   EXHAUSTED\t<times the file ran out>    (smallcrush only; > 0 means
 *                                           data was reused and results
 *                                           must not be trusted)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <testu01/unif01.h>
#include <testu01/bbattery.h>
#include <testu01/swrite.h>

static FILE *src;
static unsigned long words_used = 0;
static unsigned long exhausted = 0;

/* Big-endian 32-bit words, matching numpy.packbits bit order. */
static unsigned int next_word(void)
{
    unsigned char b[4];
    if (fread(b, 1, 4, src) != 4) {
        exhausted++;
        rewind(src);
        if (fread(b, 1, 4, src) != 4) {
            fprintf(stderr, "file shorter than one word\n");
            exit(2);
        }
    }
    words_used++;
    return ((unsigned int)b[0] << 24) | ((unsigned int)b[1] << 16) |
           ((unsigned int)b[2] << 8) | (unsigned int)b[3];
}

static void print_results(void)
{
    for (int j = 0; j < bbattery_NTests; j++) {
        if (bbattery_TestNames[j] == NULL)
            continue;
        printf("P\t%s\t%.10g\n", bbattery_TestNames[j], bbattery_pVal[j]);
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s rabbit|alphabit <file> <nbits> | smallcrush <file>\n", argv[0]);
        return 1;
    }
    swrite_Basic = FALSE;

    if (strcmp(argv[1], "rabbit") == 0 || strcmp(argv[1], "alphabit") == 0) {
        if (argc < 4) {
            fprintf(stderr, "nbits required\n");
            return 1;
        }
        double nb = atof(argv[3]);
        if (strcmp(argv[1], "rabbit") == 0)
            bbattery_RabbitFile(argv[2], nb);
        else
            bbattery_AlphabitFile(argv[2], nb);
        print_results();
    } else if (strcmp(argv[1], "smallcrush") == 0) {
        src = fopen(argv[2], "rb");
        if (!src) {
            perror("open");
            return 1;
        }
        unif01_Gen *gen = unif01_CreateExternGenBits("file", next_word);
        bbattery_SmallCrush(gen);
        unif01_DeleteExternGenBits(gen);
        fclose(src);
        print_results();
        printf("WORDS_USED\t%lu\n", words_used);
        printf("EXHAUSTED\t%lu\n", exhausted);
    } else {
        fprintf(stderr, "unknown battery %s\n", argv[1]);
        return 1;
    }
    return 0;
}
