import enum

import tensorflow as tf

from . import util
from .flag import FLAGS, add_flag, add_required_flag


MODES = [tf.contrib.learn.ModeKeys.TRAIN,
         tf.contrib.learn.ModeKeys.EVAL,
         tf.contrib.learn.ModeKeys.INFER]


def _add_file_flag(mode):
    assert isinstance(mode, str)

    flag_name = "{}_file".format(mode)
    add_required_flag(flag_name,
                      help="File path of {0} data file(s). "
                           "A glob is available. (e.g. {0}/*.tfrecords)"
                           .format(mode))
    return flag_name


def def_def_def_input_fn(mode):
    assert mode in MODES

    BATCH_SIZE = 64

    def def_def_input_fn(batch_inputs=True, prepare_filename_queues=True):
        if batch_inputs:
            add_flag("batch_size", type=int, default=BATCH_SIZE,
                     help="Mini-batch size")
            add_flag("batch_queue_capacity", type=int, default=BATCH_SIZE * 16,
                     help="Batch queue capacity")

        if prepare_filename_queues:
            file_flag = _add_file_flag(mode)
            filenames_to_queue = def_filenames_to_queue(mode)

        def def_input_fn(user_input_fn):
            @util.func_scope
            def input_fn():
                if prepare_filename_queues:
                    x, y = user_input_fn(filenames_to_queue({
                        mode: tf.train.match_filenames_once(
                            getattr(FLAGS, "{}_file".format(mode)),
                            name="{}_filenames".format(mode))
                        for mode in [tf.contrib.learn.ModeKeys.TRAIN,
                                     tf.contrib.learn.ModeKeys.EVAL]}[mode]))
                else:
                    x, y = user_input_fn()

                if not batch_inputs:
                    return x, y

                tuple_input = isinstance(x, tf.Tensor)

                if not tuple_input:
                    duplicate_keys = x.keys() & y.keys()
                    if len(duplicate_keys) != 0:
                        raise ValueError(
                            "Some keys of x and y are duplicate. ({})"
                            .format(duplicate_keys))

                inputs = (tf.train.shuffle_batch
                          if mode == tf.contrib.learn.ModeKeys.TRAIN else
                          tf.train.batch)(
                    [x, y] if tuple_input else {**x, **y},
                    batch_size=FLAGS.batch_size,
                    capacity=FLAGS.batch_queue_capacity,
                    **({"min_after_dequeue": FLAGS.batch_queue_capacity // 2}
                       if mode == tf.contrib.learn.ModeKeys.TRAIN else
                       {"allow_smaller_final_batch": True}))

                restore = lambda x: {key: inputs[key] for key in x.keys()}

                return inputs if tuple_input else (restore(x), restore(y))

            return input_fn

        return def_input_fn

    return def_def_input_fn


for mode in MODES:
    globals()["def_def_{}_input_fn".format(mode)] = def_def_def_input_fn(mode)


def def_filenames_to_queue(mode):
    assert mode in MODES

    add_flag("filename_queue_capacity", type=int, default=32,
             help="Capacity of filename queues of {}, {} and {} data"
                  .format(*MODES))

    @util.func_scope
    def filenames_to_queue(filenames):
        return tf.train.string_input_producer(
            filenames,
            num_epochs=(None
                        if mode == tf.contrib.learn.ModeKeys.TRAIN else
                        1),
            shuffle=(mode == tf.contrib.learn.ModeKeys.TRAIN),
            capacity=FLAGS.filename_queue_capacity)

    return filenames_to_queue
