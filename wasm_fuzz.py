import os
import sys
import run
import argparse
import random
from multiprocessing import Pool, Manager, Lock, current_process
from multiprocessing.sharedctypes import Value

m = Manager()
trial_count = Value('i',0)
compilation_failure = Value('i',0)

def fs_setup():
    try:
        os.mkdir("./wasm_fuzz_out")
    except:
        pass
    try:
        os.mkdir("./wasm_fuzz_out/keep")
    except:
        pass

def rand_bytes(n):
    return bytearray(random.getrandbits(8) for _ in range(n))

#gets pid at the trial generation -- need to call constructor after we have mapped
class WasmTrial(object):
  """docstring for WasmTrial"""
  def __init__(self, idx, num_rand_bytes):
    self.idx = idx
    self.pid = os.getpid()
    self.num_rand_bytes = num_rand_bytes
    self.source_file = f"wasm_fuzz_out/test_{self.pid}.txt"
    self.wasm_file = f"wasm_fuzz_out/test_{self.pid}.wasm"
    self.bin_file = f"wasm_fuzz_out/test_{self.pid}.so"
    #if this case provides a failure, this is where we save it to
    self.keep_source_path = f"wasm_fuzz_out/keep/test_{self.pid}_{self.idx}.txt"
    self.keep_wasm_path = f"wasm_fuzz_out/keep/test_{self.pid}_{self.idx}.wasm"
    self.keep_bin_path = f"wasm_fuzz_out/keep/test_{self.pid}_{self.idx}.so"

  def create_source_file(self):
        rand_b = rand_bytes(self.num_rand_bytes)
        with open(self.source_file, 'wb') as f:
            f.write(rand_b)

  def create_wasm_file(self):
        flags = f"-ttf --remove-imports"
        cmd = f"./binaryen/bin/wasm-opt {flags} {self.source_file} -o {self.wasm_file}"
        os.system(cmd)

  def create_native_code(self):
    lucet = "lucet/target/release/lucetc"
    bindings = "--bindings lucet/lucet-wasi/bindings.json"
    flags = '--guard-size "4GiB" --min-reserved-size "4GiB" --max-reserved-size "4GiB"'
    cmd = f"{lucet} {bindings} {flags} {self.wasm_file} -o {self.bin_file}"
    os.system(cmd)

  def validate_bin(self):
        run.run(self.bin_file)

  def cleanup(self):
      if os.path.isfile(f"{self.source_file}"):
          cmd1 = f"rm {self.source_file}"
          os.system(cmd1)
      try:
          if os.path.isfile(f"{self.wasm_file}"):
              cmd2 = f"rm {self.wasm_file}"
              os.system(cmd2)
      except:
          pass
      try:
          if os.path.isfile(f"{self.bin_file}"):
              cmd3 = f"rm {self.bin_file}"
              os.system(cmd3)
      except:
          pass

  def on_success(self):
    self.cleanup()

  def on_failure(self):
    print("Invoking Failure Case!")
    cmd1 = f"cp {self.source_file} {self.keep_source_path}"
    cmd2 = f"cp {self.wasm_file} {self.keep_wasm_path}"
    cmd3 = f"cp {self.bin_file} {self.keep_bin_path}"
    os.system(cmd1)
    print(cmd1)
    os.system(cmd2)
    print(cmd2)
    os.system(cmd3)
    print(cmd3)
    self.cleanup()

def run_one_test(args):
    global trial_count
    global compilation_failure
    (idx,num_rand_bytes) = args
    trial = WasmTrial(idx, num_rand_bytes)
    print(f"Running Test #{idx}")
    trial.create_source_file()
    trial.create_wasm_file()
    trial.create_native_code()
    trial_count.value += 1
    if (not os.path.isfile(trial.wasm_file)) or (not os.path.isfile(trial.bin_file)):
        trial.cleanup()
        return
    try:
      trial.validate_bin()
      trial.on_success()
    except FileNotFoundError:
      compilation_failure.value += 1
      trial.cleanup()
    except KeyboardInterrupt:
      trial.cleanup()
    except Exception as e:
      print(e)
      trial.on_failure()

def trial_args_iter(num_rand_bytes):
    idx = 0
    while True:
        yield (idx,num_rand_bytes)
        idx += 1

def dry_run(args):
    print(args)
    return True

def run_fuzzer_parallel(n=1, num_rand_bytes=8096):
    fs_setup()
    print(f"Fuzzing with {n} processes")
    pool = Pool(processes=n, maxtasksperchild=1)
    for thing in list(pool.imap_unordered(run_one_test, trial_args_iter(num_rand_bytes))):
        print(thing)
    print("Done!")

def main():
    global trial_count
    global compilation_failure
    parser = argparse.ArgumentParser(description='Run CSmith Fuzzer for Native Wasm Validator')
    parser.add_argument('-j', dest='n', default=1, help='number of jobs')
    args = parser.parse_args()
    try:
        run_fuzzer_parallel(n=int(args.n))
    except:
        pass
    print(f"{float(trial_count.value)} trials {float(compilation_failure.value)} failures")
    print(f"{float(compilation_failure.value) / float(trial_count.value)} compilation failure ratio")
   
if __name__ == '__main__':
    main()

