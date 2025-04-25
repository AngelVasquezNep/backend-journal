class EmailServiceInterface:
    @staticmethod
    def send_message(
        To,
        Subject=None,
        Content=None,
    ):
        raise NotImplementedError('send_message is not implemented')
