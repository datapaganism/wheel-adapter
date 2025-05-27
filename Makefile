setup:
	rm -rf build && mkdir build && cd build && cmake .. && cd -

me:
	cd build && make && cd -

flash:
	cp build/adapter.uf2 /media/${USER}/RPI-RP2

run:
	cd ./python-wheel && ./main.py && cd -