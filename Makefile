DEVICE := /media/$(USER)/CIRCUITPY/
ifeq ($(wildcard $(DEVICE).),)
	DEVICE := /run/media/$(USER)/CIRCUITPY/
endif

NAME = $(shell basename $(CURDIR))

SRCS := ./code.py

PICOTOOL = picotool

all: upload

upload: $(SRCS)
	@for file in $^ ; do \
		echo $${file} "=>" $(DEVICE)$${file} ; \
		cp $${file} $(DEVICE)$${file} ; \
	done

package:
	sudo $(PICOTOOL) save --all $(NAME).uf2
