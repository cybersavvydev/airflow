# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import contextlib
from functools import wraps
from inspect import signature
from typing import Callable, Iterator, TypeVar

from airflow import settings


@contextlib.contextmanager
def create_session() -> Iterator[settings.SASession]:
    """Contextmanager that will create and teardown a session."""
    session: settings.SASession = settings.Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


RT = TypeVar("RT")


def find_session_idx(func: Callable[..., RT]) -> int:
    """Find session index in function call parameter."""
    func_params = signature(func).parameters
    try:
        # func_params is an ordered dict -- this is the "recommended" way of getting the position
        session_args_idx = tuple(func_params).index("session")
    except ValueError:
        raise ValueError(f"Function {func.__qualname__} has no `session` argument") from None

    return session_args_idx


def provide_session(func: Callable[..., RT]) -> Callable[..., RT]:
    """
    Function decorator that provides a session if it isn't provided.
    If you want to reuse a session or run the function as part of a
    database transaction, you pass it to the function, if not this wrapper
    will create one and close it for you.
    """
    session_args_idx = find_session_idx(func)

    @wraps(func)
    def wrapper(*args, **kwargs) -> RT:
        if "session" in kwargs or session_args_idx < len(args):
            return func(*args, **kwargs)
        else:
            with create_session() as session:
                return func(*args, session=session, **kwargs)

    return wrapper


@provide_session
@contextlib.contextmanager
def create_global_lock(session=None, pg_lock_id=1, lock_name='init', mysql_lock_timeout=1800):
    """Contextmanager that will create and teardown a global db lock."""
    dialect = session.connection().dialect
    try:
        if dialect.name == 'postgresql':
            session.connection().execute(f'select PG_ADVISORY_LOCK({pg_lock_id});')

        if dialect.name == 'mysql' and dialect.server_version_info >= (
            5,
            6,
        ):
            session.connection().execute(f"select GET_LOCK('{lock_name}',{mysql_lock_timeout});")

        if dialect.name == 'mssql':
            # TODO: make locking works for MSSQL
            pass

        yield None
    finally:
        if dialect.name == 'postgresql':
            session.connection().execute(f'select PG_ADVISORY_UNLOCK({pg_lock_id});')

        if dialect.name == 'mysql' and dialect.server_version_info >= (
            5,
            6,
        ):
            session.connection().execute(f"select RELEASE_LOCK('{lock_name}');")

        if dialect.name == 'mssql':
            # TODO: make locking works for MSSQL
            pass
