import os
import os.path
import sys
import run
import argparse
from multiprocessing import Pool, Manager, Lock, current_process

def fs_setup():
    try:
        os.mkdir("./fuzz_out")
    except:
        pass
    try:
        os.mkdir("./fuzz_out/keep")
    except:
        pass

#gets pid at the trial generation -- need to call constructor after we have mapped
class CSmithTrial(object):
  """docstring for CSmithTrial"""
  def __init__(self, idx, cpp3=False, cpp11=False):
    self.idx = idx
    self.cpp3 = cpp3 
    self.cpp11 = cpp11
    self.is_cpp = cpp3 or cpp11
    self.pid = os.getpid()
    self.source_file = f"fuzz_out/test_{self.pid}{('.cpp' if cpp3 or cpp11 else '.c')}"
    self.wasm_file = f"fuzz_out/test_{self.pid}.wasm"
    self.bin_file = f"fuzz_out/test_{self.pid}.so"
    #if this case provides a faiulre, this is where we save it to
    self.keep_source_path = f"fuzz_out/keep/test_{self.pid}_{self.idx}{('.cpp' if cpp3 or cpp11 else '.c')}"
    self.keep_wasm_path = f"fuzz_out/keep/test_{self.pid}_{self.idx}.wasm"
    self.keep_bin_path = f"fuzz_out/keep/test_{self.pid}_{self.idx}.so"

  def create_source_file(self):
    if self.cpp3:
        cmd = f'csmith/src/csmith --lang-cpp -o {self.source_file}'
    elif self.cpp11:
        cmd = f'csmith/src/csmith --lang-cpp --cpp11 -o {self.source_file}'
    else:
        cmd = f'csmith/src/csmith -o {self.source_file}'

    #print(cmd)
    os.system(cmd)

  def create_wasm_file(self):
    clang = "./wasi-sdk-10.0/bin/clang"
    sysroot = '--sysroot ./wasi-sdk-10.0/share/wasi-sysroot/'
    flags = '-Wl,--export-all -I./csmith/runtime -w -fpermissive'
    if self.cpp3:
        cmd = f"{clang} {sysroot} {flags} --std=c++03 {self.source_file} -o {self.wasm_file}"
    elif self.cpp11:
        cmd = f"{clang} {sysroot} {flags} --std=c++11  -Wno-c++11-narrowing {self.source_file} -o {self.wasm_file}"
    else:
        cmd = f"{clang} {sysroot} {flags} {self.source_file} -o {self.wasm_file}"
    os.system(cmd)


  def create_native_code(self):
    lucet = "./lucet/target/release/lucetc"
    bindings = "--bindings ./lucet/lucet-wasi/bindings.json"
    flags = '--guard-size "4GiB" --min-reserved-size "4GiB" --max-reserved-size "4GiB"'
    cmd = f"{lucet} {bindings} {flags} {self.wasm_file} -o {self.bin_file}"
    os.system(cmd)

  def validate_bin(self):
    try:
        run.run(self.bin_file)
    except:
        print(f"============> failure on {self.bin_file}")
        return False
    return True

  def cleanup(self):
      cmd1 = f"rm {self.source_file}"
      cmd2 = f"rm {self.wasm_file}"
      cmd3 = f"rm {self.bin_file}"
      os.system(cmd1)
      os.system(cmd2)
      os.system(cmd3)

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
    idx,cpp3,cpp11 = args
    #print(f"Running Test #{idx}")
    trial = CSmithTrial(idx, cpp3, cpp11)
    print(f"Running Test #{idx}")
    trial.create_source_file()
    trial.create_wasm_file()
    trial.create_native_code()
    if not os.path.isfile(trial.bin_file):
        return
    if trial.validate_bin():
      trial.on_success()
    else:
      trial.on_failure()


def trial_args_iter():
    idx = 0
    while True:
        cpp11 = (idx % 2) == 1
        yield (idx,False,cpp11)
        idx += 1

def dry_run(args):
    print(args)
    return True


def run_fuzzer_parallel(cpp3=False, cp11=False, n=1):
    fs_setup()
    print(f"Fuzzing with {n} processes")
    pool = Pool(processes=n, maxtasksperchild=1)
    for thing in list(pool.imap_unordered(run_one_test, trial_args_iter())):
        print(thing)
    print("Done!")

def main():

    parser = argparse.ArgumentParser(description='Run CSmith Fuzzer for Native Wasm Validator')
    parser.add_argument('-j', dest='n', default=1, help='number of jobs')
    args = parser.parse_args()
    run_fuzzer_parallel(n=int(args.n))
   

if __name__ == '__main__':
    main()

