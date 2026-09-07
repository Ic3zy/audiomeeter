from core import lv2
import numpy as np

chain = lv2.Lv2Chain(n_samples=512, sample_rate=48000)

plugins = chain.get_available_plugins()
target = None

for pl in plugins:
    if pl["uri"] == "https://github.com/lucianodato/noise-repellent#adaptive":
        target = pl
        break

if target is None:
    print("Error, target None.")
    exit()

filter_idx = chain.add_filter(target["uri"])

chain.set_param(filter_idx, "reduction", 20.0)

info = chain.get_filter_info(0)
print(info)


with open("/home/abdullah/Belgeler/code_work/audiomeeter/test3/mic.raw", "rb") as f:
    raw_data = f.read()

data = np.frombuffer(raw_data, dtype=np.float32)

in_left = data[0::2]
in_right = data[1::2]

chunk_size = 512
total_chunks = len(in_left) // chunk_size

out_left_list = []
out_right_list = []

for i in range(total_chunks):
    start = i * chunk_size
    end = start + chunk_size

    in_t_l = in_left[start:end]
    in_t_r = in_right[start:end]

    out_l, out_r = chain.process(in_t_l, in_t_r)

    out_left_list.append(out_l)
    out_right_list.append(out_r)

processed_l = np.concatenate(out_left_list)
processed_r = np.concatenate(out_right_list)

out_interleaved = np.empty(len(processed_l) + len(processed_r), dtype=np.float32)
out_interleaved[0::2] = processed_l
out_interleaved[1::2] = processed_r

with open(
    "/home/abdullah/Belgeler/code_work/audiomeeter/test3/out_test.raw", "wb"
) as f:
    f.write(out_interleaved.tobytes())
