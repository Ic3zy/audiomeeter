CC = gcc
CFLAGS = -Wall -Wextra -Iinclude -g 
CFLAGS += -O3 -msse4.2 -ffast-math

PW_CFLAGS = $(shell pkg-config --cflags libpipewire-0.3)

BIQUAD_CFLAGS = -I$(CURDIR)/../rt_biquad/include
LV2_CFLAGS = -I$(CURDIR)/../lv2-api/src/include $(shell pkg-config --cflags lilv-0)
LV2_LIBS = $(shell pkg-config --libs lilv-0)

CFLAGS += $(PW_CFLAGS) $(BIQUAD_CFLAGS) $(LV2_CFLAGS) -D_REENTRANT
PW_LIBS   = -lpipewire-0.3 -lm

SRC = $(wildcard src/*.c)
OBJ = $(SRC:.c=.o)
LV2_SRC = $(CURDIR)/../lv2-api/src/lv2_manager.c
LV2_OBJ = $(CURDIR)/../lv2-api/src/lv2_manager.o

libengine.so: $(OBJ) $(LV2_OBJ)
	$(CC) -shared -o $@ $(OBJ) $(LV2_OBJ) $(PW_LIBS) $(LV2_LIBS)

$(LV2_OBJ): $(LV2_SRC)
	$(CC) $(CFLAGS) -fPIC -c $< -o $@

%.o: %.c
	$(CC) $(CFLAGS) $(PW_CFLAGS) -fPIC -c $< -o $@

test: libengine.so
	$(CC) $(CFLAGS) -o test_run test/test.c -L. -lengine $(PW_CFLAGS) $(PW_LIBS) $(LV2_LIBS) -Wl,-rpath,.
    
clean:
	rm -f $(OBJ) $(LV2_OBJ) libengine.so test_run