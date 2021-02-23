build:
	make build_csmith
	make build_binaryen
	make fetch_wasiclang
	make build_lucet

build_csmith:
	if [ ! -d ./csmith ]; then \
		git clone git@github.com:csmith-project/csmith.git && \
		cd csmith && ./configure && make ; \
	fi

build_binaryen:
	if [ ! -d ./binaryen ]; then \
		git clone git@github.com:WebAssembly/binaryen.git && \
		cd binaryen && cmake . && make ; \
	fi

fetch_wasiclang:
	if [ ! -d ./wasi-sdk-10.0/ ]; then \
		wget https://www.github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-10/wasi-sdk-10.0-linux.tar.gz && \
		tar -xzvf wasi-sdk-10.0-linux.tar.gz wasi-sdk-10.0/ && rm wasi-sdk-10.0-linux.tar.gz ; \
	fi

csmith_fuzz: #build_csmith fetch_wasiclang build_lucet
	ulimit 512000000 && nice -n 19 -- python csmith_fuzz.py -j 96

wasm_fuzz:
	ulimit 512000000 && nice -n 19 -- python wasm_fuzz.py -j 96

build_lucet:
	if [ ! -d ./lucet ]; then \
		git clone git@github.com:bytecodealliance/lucet.git && \
		cd lucet && git submodule update --init --recursive && \
		cd lucetc && cargo build ; \
	fi

