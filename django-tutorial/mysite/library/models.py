from django.db import models



class Book(models.Model):
    title = models.CharField(null=False, blank=False, max_length=100)
    authors = models.ManyToManyField('Author', related_name="books")
    summary = models.CharField(null=True, blank=True, max_length=200)
    ISBN = models.CharField(null=False, blank=False, max_length=50)
    genre = models.ForeignKey('Genre', null=True, on_delete=models.SET_NULL)
    language = models.ForeignKey('Lang', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.title} | {[str(book) for book in self.authors.all()]}"


class BookStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE"            # The book is on the shelf and can be borrowed
    CHECKED_OUT = "CHECKED_OUT"        # The book has been borrowed by a patron and is not available
    RESERVED = "RESERVED"              # A patron has requested the book and it is awaiting pickup
    ON_HOLD = "ON_HOLD"                # The book is in a queue due to multiple reservations
    OVERDUE = "OVERDUE"                # The return date has passed, and the book hasn't been returned
    LOST = "LOST"                      # The book is missing and not available in the library
    DAMAGED = "DAMAGED"                # The book has suffered damage and may be under repair
    UNDER_REPAIR = "UNDER_REPAIR"      # The book is being repaired and cannot be borrowed
    IN_TRANSIT = "IN_TRANSIT"          # The book is being transferred between library branches
    NOT_FOR_LOAN = "NOT_FOR_LOAN"      # The book is for in-library use only and cannot be taken out
    PROCESSING = "PROCESSING"          # The book has been recently acquired and is being prepared for circulation
    WITHDRAWN = "WITHDRAWN"            # The book has been removed from the collection and is no longer available



class BookInstance(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    due_back = models.DateField(null=True)
    status = models.CharField(
                max_length=20,
                null=False,
                blank=False,
                choices=BookStatus,
                default=BookStatus.AVAILABLE)

    def __str__(self):
        return f"{self.book} | {self.status}"


class Author(models.Model):
    full_name = models.CharField(null=False, blank=False, max_length=200)

    def __str__(self):
        return self.full_name


class Lang(models.Model):
    class LangChoices(models.TextChoices):
        EN = "EN"
        ES = "ES"
    name = models.CharField(
            max_length=5,
            null=False,
            blank=False,
            choices=LangChoices)

    def __str__(self):
        return self.name


class BookGenre(models.TextChoices):
    FICTION = "FICTION"
    NON_FICTION = "NON_FICTION"
    MYSTERY = "MYSTERY"
    FANTASY = "FANTASY"
    SCIENCE_FICTION = "SCIENCE_FICTION"
    ROMANCE = "ROMANCE"
    THRILLER = "THRILLER"
    YOUNG_ADULT = "YOUNG_ADULT"
    HISTORICAL_FICTION = "HISTORICAL_FICTION"
    HORROR = "HORROR"


class Genre(models.Model):
    name = models.CharField(
            null=False,
            blank=False,
            max_length=50,
            choices=BookGenre)

    def __str__(self):
        return self.name


