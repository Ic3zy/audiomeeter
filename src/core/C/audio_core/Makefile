CC = gcc
CFLAGS = -Wall -Wextra -Iinclude -g

PW_CFLAGS = $(shell pkg-config --cflags libpipewire-0.3)

BIQUAD_CFLAGS = -I$(CURDIR)/../rt_biquad/include

CFLAGS += $(PW_CFLAGS) $(BIQUAD_CFLAGS) -D_REENTRANT
PW_LIBS   = -lpipewire-0.3 -lm

SRC = $(wildcard src/*.c)
OBJ = $(SRC:.c=.o)

libengine.so: $(OBJ)
	$(CC) -shared -o $@ $(OBJ) $(PW_LIBS)

%.o: %.c
	$(CC) $(CFLAGS) $(PW_CFLAGS) -fPIC -c $< -o $@

test: libengine.so
	$(CC) $(CFLAGS) -o test_run test/test.c -L. -lengine $(PW_CFLAGS) $(PW_LIBS) -Wl,-rpath,.
    
clean:
	rm -f $(OBJ) libengine.so test_run