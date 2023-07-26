import pytest
from pathlib import Path
import shutil
import platform

import numpy as np

from spikeinterface.core import generate_recording, generate_sorting
from spikeinterface.core.waveform_tools import (
    extract_waveforms_to_buffers,
    extract_waveforms_to_single_buffer,
    split_waveforms_by_units,
)


if hasattr(pytest, "global_test_folder"):
    cache_folder = pytest.global_test_folder / "core"
else:
    cache_folder = Path("cache_folder") / "core"


def _check_all_wf_equal(list_wfs_arrays):
    wfs_arrays0 = list_wfs_arrays[0]
    for i, wfs_arrays in enumerate(list_wfs_arrays):
        for unit_id in wfs_arrays.keys():
            assert np.array_equal(wfs_arrays[unit_id], wfs_arrays0[unit_id])


def test_waveform_tools():
    durations = [30, 40]
    sampling_frequency = 30000.0

    # 2 segments
    num_channels = 2
    recording = generate_recording(
        num_channels=num_channels, durations=durations, sampling_frequency=sampling_frequency
    )
    recording.annotate(is_filtered=True)
    num_units = 15
    sorting = generate_sorting(num_units=num_units, sampling_frequency=sampling_frequency, durations=durations)

    # test with dump !!!!
    recording = recording.save()
    sorting = sorting.save()

    nbefore = int(3.0 * sampling_frequency / 1000.0)
    nafter = int(4.0 * sampling_frequency / 1000.0)

    dtype = recording.get_dtype()
    # return_scaled = False

    spikes = sorting.to_spike_vector()

    unit_ids = sorting.unit_ids

    some_job_kwargs = [
        {"n_jobs": 1, "chunk_size": 3000, "progress_bar": True},
        {"n_jobs": 2, "chunk_size": 3000, "progress_bar": True},
    ]
    some_modes = [
        {"mode": "memmap"},
    ]
    if platform.system() != "Windows":
        # shared memory on windows is buggy...
        some_modes.append(
            {
                "mode": "shared_memory",
            }
        )

    some_sparsity = [
        dict(sparsity_mask=None),
        dict(sparsity_mask=np.random.randint(0, 2, size=(unit_ids.size, recording.channel_ids.size), dtype="bool")),
    ]

    # memmap mode
    list_wfs_dense = []
    list_wfs_sparse = []
    for j, job_kwargs in enumerate(some_job_kwargs):
        for k, mode_kwargs in enumerate(some_modes):
            for l, sparsity_kwargs in enumerate(some_sparsity):
                # print()
                # print(job_kwargs, mode_kwargs, 'sparse=', sparsity_kwargs['sparsity_mask'] is None)

                if mode_kwargs["mode"] == "memmap":
                    wf_folder = cache_folder / f"test_waveform_tools_{j}_{k}_{l}"
                    if wf_folder.is_dir():
                        shutil.rmtree(wf_folder)
                    wf_folder.mkdir(parents=True)
                    mode_kwargs_ = dict(**mode_kwargs, folder=wf_folder)
                else:
                    mode_kwargs_ = mode_kwargs

                wfs_arrays = extract_waveforms_to_buffers(
                    recording,
                    spikes,
                    unit_ids,
                    nbefore,
                    nafter,
                    return_scaled=False,
                    dtype=dtype,
                    copy=True,
                    **sparsity_kwargs,
                    **mode_kwargs_,
                    **job_kwargs,
                )
                for unit_ind, unit_id in enumerate(unit_ids):
                    wf = wfs_arrays[unit_id]
                    assert wf.shape[0] == np.sum(spikes["unit_index"] == unit_ind)

                if sparsity_kwargs["sparsity_mask"] is None:
                    list_wfs_dense.append(wfs_arrays)
                else:
                    list_wfs_sparse.append(wfs_arrays)

                all_waveforms = extract_waveforms_to_single_buffer(
                    recording,
                    spikes,
                    unit_ids,
                    nbefore,
                    nafter,
                    return_scaled=False,
                    dtype=dtype,
                    copy=True,
                    **sparsity_kwargs,
                    **mode_kwargs_,
                    **job_kwargs,
                )
                wfs_arrays = split_waveforms_by_units(
                    unit_ids, spikes, all_waveforms, sparsity_mask=sparsity_kwargs["sparsity_mask"]
                )
                if sparsity_kwargs["sparsity_mask"] is None:
                    list_wfs_dense.append(wfs_arrays)
                else:
                    list_wfs_sparse.append(wfs_arrays)

    _check_all_wf_equal(list_wfs_dense)
    _check_all_wf_equal(list_wfs_sparse)


if __name__ == "__main__":
    test_waveform_tools()
