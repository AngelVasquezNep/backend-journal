from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from recipe.models import RecipeAttributeType, CreatedBy

User = get_user_model()


RECIPE_DATA = {
    "INGREDIENT": [
        ["Tomato", "TOMATO"],
        ["Chicken", "CHICKEN"],
        ["Onion", "ONION"],
        ["Garlic", "GARLIC"],
        ["Basil", "BASIL"],
        ["Olive Oil", "OLIVE_OIL"],
        ["Avocado", "AVOCADO"],
        ["Rice", "RICE"],
        ["Salt", "SALT"],
        ["Pepper", "PEPPER"],
        ["Spinach", "SPINACH"],
        ["Carrot", "CARROT"],
        ["Potatoes", "POTATOES"],
        ["Bell Pepper", "BELL_PEPPER"],
        ["Cucumber", "CUCUMBER"],
        ["Pasta", "PASTA"],
        ["Egg", "EGG"],
        ["Pancetta", "PANCETTA"],
        ["Parmesan Cheese", "PARMESAN_CHEESE"],
        ["Black Pepper", "BLACK_PEPPER"],
        ["Mozzarella", "MOZZARELLA"],
    ],
    "KEYWORD": [
        ["Vegan", "VEGAN"],
        ["Gluten-Free", "GLUTEN_FREE"],
        ["Low-Carb", "LOW_CARB"],
        ["High-Protein", "HIGH_PROTEIN"],
        ["Quick", "QUICK"],
        ["Easy", "EASY"],
        ["Spicy", "SPICY"],
        ["Sweet", "SWEET"],
        ["Comfort Food", "COMFORT_FOOD"],
        ["Family-Friendly", "FAMILY_FRIENDLY"],
        ["Keto", "KETO"],
        ["Dairy-Free", "DAIRY_FREE"],
        ["Low-Fat", "LOW_FAT"],
        ["High-Fiber", "HIGH_FIBER"],
        ["Summer", "SUMMER"]
    ],
    "CUISINE": [
        ["Italian", "ITALIAN"],
        ["Mexican", "MEXICAN"],
        ["Chinese", "CHINESE"],
        ["Indian", "INDIAN"],
        ["Thai", "THAI"],
        ["French", "FRENCH"],
        ["Mediterranean", "MEDITERRANEAN"],
        ["American", "AMERICAN"],
        ["Japanese", "JAPANESE"],
        ["Greek", "GREEK"],
        ["Spanish", "SPANISH"],
        ["Middle Eastern", "MIDDLE_EASTERN"],
        ["Korean", "KOREAN"],
        ["Lebanese", "LEBANESE"],
        ["Vietnamese", "VIETNAMESE"],
    ],
    "DIETARY": [
        ["Vegetarian", "VEGETARIAN"],
        ["Pescatarian", "PESCATARIAN"],
        ["Paleo", "PALEO"],
        ["Whole30", "WHOLE30"],
        ["Low-Sodium", "LOW_SODIUM"],
        ["Diabetic-Friendly", "DIABETIC_FRIENDLY"],
        ["Raw Food", "RAW_FOOD"],
        ["Halal", "HALAL"],
        ["Kosher", "KOSHER"],
        ["FODMAP", "FODMAP"],
        ["Low-Glycemic", "LOW_GLYCEMIC"],
        ["Heart-Healthy", "HEART_HEALTHY"],
        ["Dairy-Free", "DAIRY_FREE"],
        ["Nut-Free", "NUT_FREE"],
        ["Sugar-Free", "SUGAR_FREE"]
    ]
}


class Command(BaseCommand):
    help = "Set up the database with some initial data"

    def handle(self, *args, **options):
        # Create a system user
        system_user = User.objects.get_system_user()

        print("Creating RecipeAttributeType objects", system_user)


        # Create RecipeAttributeType objects
        recipe_attribute_types=[]
        for recipe_attribute_type in RECIPE_DATA:
            for (label, value) in RECIPE_DATA[recipe_attribute_type]:
                existing_attribute = RecipeAttributeType.objects.filter(
                    label=label, value=value, relation_type=recipe_attribute_type
                ).first()
                if existing_attribute:
                    continue
                attribute = RecipeAttributeType(
                    label=label,
                    value=value,
                    created_by=CreatedBy.SYSTEM,
                    relation_type=recipe_attribute_type,
                    author=system_user,
                )
                recipe_attribute_types.append(attribute)

        RecipeAttributeType.objects.bulk_create(recipe_attribute_types)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up the database with some initial data. {len(recipe_attribute_types)} RecipeAttributeType objects created')
        )
