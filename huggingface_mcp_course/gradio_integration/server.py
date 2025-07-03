import gradio as gr


def letter_counter(word: str, letter: str) -> int:
    """
    Count the number of occurrence of a letter within a word (e.g. "strawberry" has 3 'r's)
    :param word: The input text to search through
    :param letter: The letter to search for
    :return: The number of times the letter appears in the text
    """
    # Account for the case of the input text and letter
    word = word.lower()
    letter = letter.lower()

    # Count the number of occurrence
    count = word.count(letter)
    return count

# Create a standard Gradio interface
demo = gr.Interface(
    fn=letter_counter,
    inputs=['textbox', 'textbox'],
    outputs='number',
    title='Letter Counter',
    description='Enter text and a letter to count how many times the letter appears in the text'
)

# Launch both the Gradio web interface and the MCP server
if __name__ == "__main__":
    demo.launch(mcp_server=True)
