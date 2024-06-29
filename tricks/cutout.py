class Cutouter:
    def __init__(self,
                 cont:str,
                 autostart: bool=True,
                 autoplow: bool=False,
                 autoreset: bool=False,
                 max_reach: int|bool=False,
                 start_pos: int = 0,
                 **kwargs
        ):
        self.start_ix:int = 0
        self.end_ix:int = 0
        self.current_pos:int = start_pos
        self.org_cont:str = cont
        self.cont:str = self.org_cont
        self.autoplow: bool = autoplow
        self.autoreset: bool = autoreset
        self.max_reach:int|bool = max_reach
        self.text:str = ""
        if autostart:
            self(**kwargs)

    def get_text(self) -> str:
        if bool(self):
            start: int = self.get_start_ix()
            end: int = self.get_end_ix()
            return self.cont[start : end]
        return ""

    def get_start_ix(self) -> int:
        return self.current_pos + self.start_ix

    def get_end_ix(self) -> int:
        return self.current_pos + self.start_ix + self.end_ix

    def __bool__(self) -> bool:
        return all(x != -1 for x in [self.start_ix, self.end_ix])

    def __repr__(self) -> str:
        return self.get_text()

    def __call__(self,
                 reset: bool = False,
                 first_find: str | list | tuple = "",
                 then_find: str | list | tuple = "",
                 jump_forward: bool | int | str = True,
                 sensetive: bool=True,
                 plow: bool = False,
                 **kwargs) -> str:

        if self.autoreset or reset:
            self.current_pos:int = 0
            self.start_ix:int = 0
            self.end_ix:int = 0

        first_find: list = [first_find] if isinstance(first_find, str) else first_find
        then_find: list = [then_find] if isinstance(then_find, str) else then_find

        for i in [x for x in first_find if x and self.start_ix != -1]:
            cut = self.cont[self.current_pos + self.start_ix:].find(i)
            if sensetive and cut == -1:
                self.start_ix = -1
                break
            elif cut != -1:
                self.start_ix += cut
                if jump_forward:
                    self.start_ix += len(i)

        for i in [x for x in then_find if x and self.start_ix != -1]:
            if self.max_reach:
                max_reach = (self.current_pos + self.start_ix) + self.max_reach
                max_reach = min(max_reach, len(self.cont))
                cut = self.cont[self.current_pos + self.start_ix: max_reach].find(i)
            else:
                cut = self.cont[self.current_pos + self.start_ix: ].find(i)

            if sensetive and cut == -1:
                self.end_ix = -1
                break
            elif cut != -1:
                self.end_ix = cut

        if (self.autoplow or plow) and bool(self):
            self.current_pos = self.get_start_ix()
            self.start_ix = 0
            self.autoreset = False

        self.text = self.get_text()
        return self.text

#
# class Cutouter:
#     def __init__(self,
#                  cont:str,
#                  autostart: bool=True,
#                  autoplow: bool=False,
#                  autoreset: bool=False,
#                  max_reach: int|bool=False,
#                  start_pos: int = 0,
#                  **kwargs
#         ):
#         self.start_ix:int = 0
#         self.end_ix:int = 0
#         self.current_pos:int = start_pos
#         self.org_cont:str = cont
#         self.cont:str = self.org_cont
#         self.autoplow: bool = autoplow
#         self.autoreset: bool = autoreset
#         self.max_reach:int|bool = max_reach
#         self.text:str = ""
#         if autostart:
#             self(**kwargs)
#
#     def get_text(self) -> str:
#         if bool(self):
#             start: int = self.get_start_ix()
#             end: int = self.get_end_ix()
#             return self.cont[start : end]
#         return ""
#
#     def get_start_ix(self) -> int:
#         return self.current_pos + self.start_ix
#
#     def get_end_ix(self) -> int:
#         return self.current_pos + self.start_ix + self.end_ix
#
#     def __bool__(self) -> bool:
#         return all(x != -1 for x in [self.start_ix, self.end_ix])
#
#     def __repr__(self) -> str:
#         return self.get_text()
#
#     def __call__(self,
#                  reset: bool = False,
#                  first_find: str | list | tuple = "",
#                  then_find: str | list | tuple = "",
#                  jump_forward: bool | int | str = True,
#                  sensetive: bool=True,
#                  plow: bool = False,
#                  **kwargs) -> str:
#
#         if self.autoreset or reset:
#             self.current_pos:int = 0
#             self.start_ix:int = 0
#             self.end_ix:int = 0
#
#         first_find: list = [first_find] if isinstance(first_find, str) else first_find
#         then_find: list = [then_find] if isinstance(then_find, str) else then_find
#
#         for i in [x for x in first_find if x and self.start_ix != -1]:
#             cut = self.cont[self.current_pos + self.start_ix:].find(i)
#             if sensetive and cut == -1:
#                 self.start_ix = -1
#                 break
#             elif cut != -1:
#                 self.start_ix += cut
#                 if jump_forward:
#                     self.start_ix += len(i)
#
#         for i in [x for x in then_find if x and self.start_ix != -1]:
#             if self.max_reach:
#                 max_reach = (self.current_pos + self.start_ix) + self.max_reach
#                 max_reach = min(max_reach, len(self.cont))
#                 cut = self.cont[self.current_pos + self.start_ix: max_reach].find(i)
#             else:
#                 cut = self.cont[self.current_pos + self.start_ix: ].find(i)
#
#             if sensetive and cut == -1:
#                 self.end_ix = -1
#                 break
#             elif cut != -1:
#                 self.end_ix = cut
#
#         if (self.autoplow or plow) and bool(self):
#             self.current_pos = self.get_start_ix()
#             self.start_ix = 0
#             self.autoreset = False
#
#         self.text = self.get_text()
#         return self.text
#
# # with open('/home/plutonergy/tmp/PLMTG_v4/16a2f666a9d90a5947dc1b2cc15d7d2d.html') as f:
# #     cont = f.read()
# #     kwgs = dict(first_find=['/Magic/Products/Singles/'], then_find='?', plow=True, max_reach=128)
# #     co = Cutouter(cont, **kwgs)
# #     vars = {}
# #     while bool(co):
# #         try:
# #             vars[co.text()] += 1
# #         except KeyError:
# #             vars[co.text()] = 1
# #         co(**kwgs)
# #
# #     if vars:
# #         vars = [(k, v) for k, v in vars.items()]
# #         vars.sort(key=lambda x: x[1], reverse=True)
# #         url = f'https://www.cardmarket.com/en/Magic/Expansions/{vars[0][0]}'
# #         print(url)