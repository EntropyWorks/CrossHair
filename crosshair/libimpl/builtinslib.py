import collections
import contextlib
import io
import re
import typing
from typing import *

from crosshair.core import register_type, realize
from crosshair.core import SmtBool, SmtInt, SmtFloat, SmtStr, SmtList, SmtDict
from crosshair.core import SmtMutableSet, SmtFrozenSet, SmtType, SmtCallable

from crosshair.util import IgnoreAttempt, debug


def pick_union(creator, *pytypes):
    for typ in pytypes[:-1]:
        if creator.space.smt_fork():
            return creator(typ)
    return creator(pytypes[-1])

def make_optional_smt(smt_type):
    def make(creator, *type_args):
        ret = smt_type(creator.space, creator.pytype, creator.varname)
        if creator.space.fork_parallel(false_probability=0.98):
            ret = realize(ret)
            debug('Prematurely realized', creator.pytype, 'value')
        return ret
    return make

def make_raiser(exc, *a) -> Callable:
    def do_raise(*ra, **rkw) -> NoReturn:
        raise exc(*a)
    return do_raise

def make_registrations():

    register_type(Union, pick_union)

    # Types modeled in the SMT solver:

    register_type(type(None), lambda *a: None)
    register_type(bool, make_optional_smt(SmtBool))
    register_type(int, make_optional_smt(SmtInt))
    register_type(float, make_optional_smt(SmtFloat))
    register_type(str, make_optional_smt(SmtStr))
    register_type(list, make_optional_smt(SmtList))
    register_type(dict, make_optional_smt(SmtDict))
    register_type(set, make_optional_smt(SmtMutableSet))
    register_type(frozenset, make_optional_smt(SmtFrozenSet))
    register_type(type, make_optional_smt(SmtType))
    register_type(collections.abc.Callable, make_optional_smt(SmtCallable))

    # Most types are not directly modeled in the solver, rather they are built
    # on top of the modeled types. Such types are enumerated here:
    
    register_type(complex, lambda p: complex(p(float), p(float)))
    register_type(type(None), lambda p: None)
    register_type(slice, lambda p: slice(p(Optional[int]), p(Optional[int]), p(Optional[int])))
    register_type(NoReturn, make_raiser(IgnoreAttempt, 'Attempted to short circuit a NoReturn function')) # type: ignore
    
    # AsyncContextManager, lambda p: p(contextlib.AbstractAsyncContextManager),
    # AsyncGenerator: ,
    # AsyncIterable,
    # AsyncIterator,
    # Awaitable,
    # Coroutine: (handled via typeshed)
    # Generator: (handled via typeshed)
    
    register_type(NamedTuple, lambda p, *t: p(Tuple.__getitem__(tuple(t))))
    
    register_type(re.Pattern, lambda p, t=None: p(re.compile))  # type: ignore
    register_type(re.Match, lambda p, t=None: p(re.match))  # type: ignore
    
    # Text: (elsewhere - identical to str)
    register_type(bytes, lambda p: p(ByteString))
    register_type(bytearray, lambda p: p(ByteString))
    register_type(memoryview, lambda p: p(ByteString))
    # AnyStr,  (it's a type var)
    
    register_type(typing.BinaryIO, lambda p: io.BytesIO(p(ByteString)))
    # TODO: handle Any/AnyStr with a custom class that accepts str/bytes interchangably?:
    register_type(typing.IO, lambda p, t=Any: p(BinaryIO) if t == 'bytes' else p(TextIO))
    # TODO: StringIO (and BytesIO) won't accept SmtStr writes.
    # Consider clean symbolic implementations of these.
    register_type(typing.TextIO, lambda p: io.StringIO(str(p(str))))
    
    register_type(SupportsAbs, lambda p: p(int))
    register_type(SupportsFloat, lambda p: p(float))
    register_type(SupportsInt, lambda p: p(int))
    register_type(SupportsRound, lambda p: p(float))
    register_type(SupportsBytes, lambda p: p(ByteString))
    register_type(SupportsComplex, lambda p: p(complex))

