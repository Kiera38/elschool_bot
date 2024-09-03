import typing
from contextlib import asynccontextmanager

from aiogram.fsm import scene


class Scene(scene.Scene):
    def __init_subclass__(cls, **kwargs):
        no_state = kwargs.pop('no_state', False)
        state_name = kwargs.pop('state', None if no_state else cls.__name__)
        state_type = kwargs.pop('state_type', None)
        super().__init_subclass__(state=state_name, **kwargs)
        cls.state_type = state_type

    @asynccontextmanager
    async def state_data(self):
        data = state = await self.wizard.get_data()
        if self.state_type is not None:
            data = self.state_type(state)
        yield data
        await self.wizard.set_data(state)

    async def enter(self, **kwargs):
        await self.wizard.enter(**kwargs)

    async def back(self, **kwargs):
        await self.wizard.back(**kwargs)

    async def exit(self, **kwargs):
        await self.wizard.exit(**kwargs)

    async def goto(self, **kwargs):
        await self.wizard.goto(**kwargs)

    async def leave(self, _with_history=True, **kwargs):
        await self.wizard.leave(_with_history, **kwargs)

    async def retake(self, **kwargs):
        await self.wizard.retake(**kwargs)

    @property
    def data(self):
        return self.wizard.data

    @property
    def manager(self):
        return self.wizard.manager

    @property
    def event(self):
        return self.wizard.event

    @property
    def state(self):
        return self.wizard.state

    @property
    def scene_config(self):
        return self.wizard.scene_config

    @property
    def update_type(self):
        return self.wizard.update_type


@typing.dataclass_transform()
class State:
    def __init_subclass__(cls, **kwargs):
        annotations = cls.__annotations__
        no_default = object()
        for name in annotations:
            default = getattr(cls, name, no_default)
            if default == no_default:
                def fget(self):
                    return self.data[name]

            else:
                def fget(self):
                    return self.data.get(name, default)

            def fset(self, value):
                self.data[name] = value

            setattr(cls, name, property(fget, fset))
        super().__init_subclass__(**kwargs)

    def __init__(self, data: dict):
        self.data = data
