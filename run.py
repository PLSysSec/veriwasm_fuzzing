import subprocess

class VerificationError(Exception):
    pass

def run(filename):   
    return_code = subprocess.call(['../target/release/veriwasm', '--enable_zero_cost_checks', \
                                   '-i', filename],\
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if return_code != 0:
        raise VerificationError
    print("Safe")

