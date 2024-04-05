import openai
from IPython.core.magic import (Magics, magics_class, line_magic)
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import PygmentsTokens
from pygments.lexers.markup import MarkdownLexer
from pygments.lexers.python import PythonLexer
from pygments import lex

from prompt_toolkit.shortcuts import confirm


@magics_class
class GPT(Magics):

    def _sample(self, line, system_message) -> str:
        history = self._history_lines()
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                system_message,
                {"role": "user", "content": history},
                {"role": "user", "content": line},
            ],
            max_tokens=2000,
            stream=True,
        )
        current_line = ""
        for chunk in response:
            if chunk.choices:
                c = chunk.choices[0].delta.content
                if c:
                    current_line += c
                    if "\n" in current_line:
                        yield current_line
                        current_line = ""
        if current_line:
            yield current_line

    def _history_lines(self):
        history = self.shell.history_manager.get_range(output=True)
        history_lines = []
        for session, line_number, input_output in history:
            inp, out = input_output
            history_lines.append(f"In [{line_number}]: {inp}")
            if out is not None:
                history_lines.append(f"Out[{line_number}]: {str(out)}\n")
            else:
                history_lines.append("\n")
        return '\n'.join(history_lines)

    @line_magic
    def ask(self, line):
        lexer = MarkdownLexer()
        sys_message = {
            "role": "system",
            "content": """
            You are a python coding assistant, running in an ipython session.
            Be concise and tailor your answers for a staff level engineer.
            You may use markdown.
            """
        }
        for sampled_line in self._sample(line, sys_message):
            print_lexed(sampled_line, lexer)

    @line_magic
    def gen(self, line):
        lexer = PythonLexer()
        sys_message = {
            "role": "system",
            "content": """
            You are a python codebot, running in an ipython session.
            Respond ONLY in python source code. Do not use markdown.
            """
        }
        full_response = ""
        for sampled_line in self._sample(line, sys_message):
            full_response += sampled_line
            print_lexed(sampled_line, lexer)
        print("\n")
        if confirm("Run it?"):
            code = trim_markdown(full_response)
            self.shell.run_cell(code)


def print_lexed(line: str, lexer) -> None:
    tokens = list(lex(line, lexer))
    print_formatted_text(PygmentsTokens(tokens), end="")


def trim_markdown(inp: str) -> str:
    def delete_prefix(prefix, text):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

    def delete_suffix(suffix, text):
        if text.endswith(suffix):
            return text[:-len(suffix)]
        return text

    return delete_prefix("python", delete_prefix("```", delete_suffix("```", inp.strip().rstrip())))
