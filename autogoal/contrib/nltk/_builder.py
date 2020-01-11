import nltk
import nltk.stem as st
import nltk.tokenize as tk
import sklearn


import textwrap
import datetime
import inspect
import re
import enlighten
import numpy as np
import warnings

from pathlib import Path

from autogoal.grammar import Discrete, Continuous, Categorical, Boolean


def build_nltk_wrappers():
    imports = _walk(nltk)
    
    manager = enlighten.get_manager()
    counter = manager.counter(total=len(imports), unit="classes")

    with open(Path(__file__).parent / "_generated.py", "w") as fp:
        fp.write(textwrap.dedent(
            f"""
            # AUTOGENERATED ON {datetime.datetime.now()}
            ## DO NOT MODIFY THIS FILE MANUALLY

            from autogoal.grammar import Continuous, Discrete, Categorical, Boolean
            from numpy import inf, nan
            """
        ))
        
        for cls in imports:
            counter.update()
            _write_class(cls, fp)

    counter.close()
    manager.stop()


def _write_class(cls, fp):
    args = _get_args(cls)
    s = " " * 4
    args_str = f",\n{s * 4}".join(f"{key}: {value}" for key, value in args.items())
    self_str = f"\n{s * 4}".join(f"self.{key}={key}" for key in args)
    init_str = f",\n{s * 5}".join(f"{key}={key}" for key in args)

    print(cls)

    fp.write(textwrap.dedent(
        f"""
        from {cls.__module__} import {cls.__name__} as _{cls.__name__}

        class {cls.__name__}(_{cls.__name__}):
            def __init__(
                self,
                {args_str}
            ):
                {self_str}

                super().__init__(
                    {init_str}
                )

        """
    ))

    fp.flush()


def _is_stemmer(cls, verbose=False):
    if hasattr(cls, "stem"):
        return True
    return False

def _is_tokenizer(cls, verbose=False):
    if not "sentence" in str.lower(cls.__name__):
        if hasattr(cls, "tokenize"):
            return True
    return False

def _walk(module, name="nltk"):
    imports = []

    def _walk_p(module, name="nltk"):
        all_elements = dir(module)
        for elem in all_elements:

            if elem == "exceptions":
                continue

            name = name + "." + elem

            try:
                obj = getattr(module, elem)

                if isinstance(obj, type):
                    #ignore nltk interfaces
                    if name.endswith("I"):
                        continue

                    if not (_is_tokenizer(obj) or _is_stemmer(obj)):
                        continue
                    
                    print("Found:", elem)
                    imports.append(obj)

                # _walk_p(obj, name) If not module do not walk in it
            except Exception as e:
                pass

            try:
                inner_module = importlib.import_module(name)
                _walk_p(inner_module, name)
            except:
                pass

    _walk_p(module, name)

    imports.sort(key=lambda c: (c.__module__, c.__name__))
    return imports

def _find_parameter_values(parameter, cls):
    documentation = []
    lines = cls.__doc__.split("\n")

    while lines:
        l = lines.pop(0)
        if l.strip().startswith(parameter):
            documentation.append(l)
            tabs = l.index(parameter)
            break

    while lines:
        l = lines.pop(0)

        if not l.strip():
            continue

        if l.startswith(" " * (tabs + 1)):
            documentation.append(l)
        else:
            break

    options = set(re.findall(r"'(\w+)'", " ".join(documentation)))
    valid = []
    invalid = []
    skip = set(["deprecated", "auto_deprecated", "precomputed"])

    for opt in options:
        opt = opt.lower()
        if opt in skip:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cls(**{parameter: opt}).fit(np.ones((10, 10)), [True] * 5 + [False] * 5)
                valid.append(opt)
        except Exception as e:
            invalid.append(opt)

    return sorted(valid)

def _get_args(cls):
    specs = inspect.getfullargspec(cls.__init__)

    args = specs.args
    specs = specs.defaults

    if not args or not specs:
        return {}

    args = args[-len(specs) :]

    args_map = {k: v for k, v in zip(args, specs)}

    drop_args = [
        "url",
        "n_jobs",
        "max_iter",
        "class_weight",
        "warm_start",
        "copy_X",
        "copy_x",
        "copy",
        "eps",
    ]

    for arg in drop_args:
        args_map.pop(arg, None)

    result = {}

    for arg, value in args_map.items():
        values = _get_arg_values(arg, value, cls)
        if not values:
            continue
        result[arg] = values

    return result


def _get_arg_values(arg, value, cls):
    if isinstance(value, bool):
        return Boolean()
    if isinstance(value, int):
        return Discrete(*_get_integer_values(arg, value, cls))
    if isinstance(value, float):
        return Continuous(*_get_float_values(arg, value, cls))
    if isinstance(value, str):
        values = _find_parameter_values(arg, cls)
        return Categorical(*values) if values else None

    return None

def _get_integer_values(arg, value, cls):
    if value == 0:
        min_val = -100
        max_val = 100
    else:
        min_val = value // 2
        max_val = 2 * value

    return min_val, max_val

def _get_float_values(arg, value, cls):
    if value == 0:
        min_val = -1
        max_val = 1
    elif 0 < value <= 0.1:
        min_val = value / 100
        max_val = 1
    elif 0 < value <= 1:
        min_val = 1e-6
        max_val = 1
    else:
        min_val = value / 2
        max_val = 2 * value

    return min_val, max_val


if __name__ == "__main__":
    build_nltk_wrappers()
