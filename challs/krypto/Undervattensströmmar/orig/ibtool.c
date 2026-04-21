#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define HEADER_SIZE 14
#define HEADER "IBTOOLBACKUP\x00\x00"

typedef struct {
    uint16_t multiplier;
    uint16_t increment;
    uint16_t modulus;
} Params;

static int debug_mode = 0;

int parse_args(int argc, char *argv[], uint16_t *seed, char **input_file, char **output_file) {
    *seed = 0;
    *input_file = NULL;
    *output_file = NULL;
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--seed") == 0) {
            if (i + 1 < argc) {
                *seed = (uint16_t)strtoul(argv[++i], NULL, 10);
            } else {
                fprintf(stderr, "Error: --seed requires a value\n");
                return -1;
            }
        } else if (strcmp(argv[i], "--debug") == 0) {
            debug_mode = 1;
        } else if (*input_file == NULL) {
            *input_file = argv[i];
        } else if (*output_file == NULL) {
            *output_file = argv[i];
        } else {
            fprintf(stderr, "Error: Too many arguments\n");
            return -1;
        }
    }
    
    if (*input_file == NULL || *output_file == NULL) {
        fprintf(stderr, "Error: Input and output files required\n");
        return -1;
    }
    
    return 0;
}

int read_parameters(const char *filename, Params *params) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        perror("Error opening file \"parameters\"");
        return -1;
    }
    
    if (fscanf(file, "%hu", &params->multiplier) != 1 ||
        fscanf(file, "%hu", &params->increment) != 1 ||
        fscanf(file, "%hu", &params->modulus) != 1) {
        fprintf(stderr, "Error reading parameters from file.\nPlease use the parameters file provided upon purchase of IBTOOL or specify three custom integer parameters in a newline-delimited file");
        fclose(file);
        return -1;
    }
    
    fclose(file);
    
    if (params->modulus == 0) {
        fprintf(stderr, "Error: modulus cannot be zero\n");
        return -1;
    }
    
    return 0;
}

int verify_header(FILE *file) {
    char header[HEADER_SIZE];
    
    long current_pos = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    if (fread(header, 1, HEADER_SIZE, file) != HEADER_SIZE) {
        fprintf(stderr, "Error: Could not read file header\n");
        return -1;
    }
    
    fseek(file, current_pos, SEEK_SET);
    
    if (memcmp(header, HEADER, HEADER_SIZE) != 0) {
        fprintf(stderr, "Error: File is not a valid IBTOOL backup file.\n");
        return -1;
    }
    
    return 0;
}
/*
uint16_t generate_next_keystream(Params *params, uint16_t *current_state) {
    *current_state = (params->multiplier * (*current_state) + params->increment) % params->modulus;

    uint32_t delay = *current_state & 0x1FFF; 
    volatile uint32_t accumulator = 0;
    
    for (uint32_t i = 0; i < delay; i++) {
        for (uint32_t j = 0; j < 1000; j++) {
            accumulator += i ^ j;
        }
    }

    return *current_state;
}
*/
static uint16_t generate_next_keystream(const Params *params, uint16_t *state)
{
    uint32_t tmp = (uint32_t)params->multiplier *
                   (uint32_t)(*state) +
                   (uint32_t)params->increment;

    uint32_t delay = *state & 0x1FFF; 
    volatile uint32_t accumulator = 0;

    for (uint32_t i = 0; i < delay; i++) {
        for (uint32_t j = 0; j < 1000; j++) {
            accumulator += i ^ j;
        }
    }

    *state = (uint16_t)(tmp % (uint32_t)params->modulus);
    return *state;
}

int encrypt_file(Params *params, uint16_t seed, const char *input_filename, const char *output_filename) {
    FILE *input_file = fopen(input_filename, "rb");
    if (!input_file) {
        perror("Error opening input file");
        return -1;
    }
    
    FILE *output_file = fopen(output_filename, "wb");
    if (!output_file) {
        perror("Error opening output file");
        fclose(input_file);
        return -1;
    }
    
    if (verify_header(input_file) != 0) {
        fclose(input_file);
        fclose(output_file);
        return -1;
    }
    
    uint16_t current_state = seed;
    
    uint16_t *keystream_values = NULL;
    int keystream_count = 0;
    int keystream_capacity = 0;
    
    if (debug_mode) {
        keystream_capacity = 1000;
        keystream_values = malloc(keystream_capacity * sizeof(uint16_t));
        if (!keystream_values) {
            fprintf(stderr, "Error allocating memory for debug output\n");
            fclose(input_file);
            fclose(output_file);
            return -1;
        }
    }
    
    uint16_t plaintext_word;
    long word_count = 0;
    while (fread(&plaintext_word, sizeof(uint16_t), 1, input_file) == 1) {
        uint16_t keystream_value = generate_next_keystream(params, &current_state);
        
        if (debug_mode) {
            if (keystream_count >= keystream_capacity) {
                keystream_capacity *= 2;
                keystream_values = realloc(keystream_values, keystream_capacity * sizeof(uint16_t));
                if (!keystream_values) {
                    fprintf(stderr, "Error reallocating memory for debug output\n");
                    fclose(input_file);
                    fclose(output_file);
                    return -1;
                }
            }
            keystream_values[keystream_count++] = keystream_value;
        }
        
        uint16_t ciphertext_word = plaintext_word ^ keystream_value;
        
        fwrite(&ciphertext_word, sizeof(uint16_t), 1, output_file);
        word_count++;
    }
    
    long file_size = ftell(input_file);
    if (file_size % 2 == 1) {
        fseek(input_file, -1, SEEK_END);
        int remaining_byte = fgetc(input_file);
        if (remaining_byte != EOF) {
            uint16_t keystream_value = generate_next_keystream(params, &current_state);
            
            if (debug_mode) {
                if (keystream_count >= keystream_capacity) {
                    keystream_capacity *= 2;
                    keystream_values = realloc(keystream_values, keystream_capacity * sizeof(uint16_t));
                    if (!keystream_values) {
                        fprintf(stderr, "Error reallocating memory for debug output\n");
                        fclose(input_file);
                        fclose(output_file);
                        return -1;
                    }
                }
                keystream_values[keystream_count++] = keystream_value;
            }
            
            uint8_t encrypted_byte = (uint8_t)(remaining_byte ^ (keystream_value & 0xFF));
            fputc(encrypted_byte, output_file);
        }
    }
    
    fclose(input_file);
    fclose(output_file);
    
    if (debug_mode && keystream_values) {
        printf("// Keystream used for encryption (first %d values)\n", keystream_count);
        printf("uint16_t keystream[] = {");
        for (int i = 0; i < keystream_count; i++) {
            if (i % 8 == 0) {
                printf("\n    ");
            }
            printf("%u", keystream_values[i]);
            if (i < keystream_count - 1) {
                printf(", ");
            }
        }
        printf("\n};\n");
        printf("// Total keystream values: %d\n", keystream_count);
        free(keystream_values);
    }
    
    return 0;
}

int main(int argc, char *argv[]) {
    uint16_t seed;
    char *input_file, *output_file;
    Params params;
    
    if (parse_args(argc, argv, &seed, &input_file, &output_file) != 0) {
        fprintf(stderr, "Usage: %s [--debug] --seed <seed_value> <input_file> <output_file>\n", argv[0]);
        return 1;
    }
    
    if (read_parameters("parameters", &params) != 0) {
        return 1;
    }
    
    if (encrypt_file(&params, seed, input_file, output_file) != 0) {
        return 1;
    }
    
    printf("File encrypted successfully!\n");
    return 0;
}
