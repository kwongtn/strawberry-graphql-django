import dataclasses
import textwrap

import strawberry
from django.db import models
from strawberry.types import get_object_definition

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.utils.typing import get_django_definition


def test_non_dataclass_annotations_are_ignored_on_type():
    class SomeModel(models.Model):
        name = models.CharField(max_length=255)

    class NonDataclass:
        non_dataclass_attr: str

    @dataclasses.dataclass
    class SomeDataclass:
        some_dataclass_attr: str

    @strawberry.type
    class SomeStrawberryType:
        some_strawberry_attr: str

    @strawberry_django.type(SomeModel)
    class SomeModelType(SomeStrawberryType, SomeDataclass, NonDataclass):
        name: str

    @strawberry.type
    class Query:
        my_type: SomeModelType

    schema = strawberry.Schema(query=Query)
    expected = """\
    type Query {
      myType: SomeModelType!
    }

    type SomeModelType {
      someStrawberryAttr: String!
      someDataclassAttr: String!
      name: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


def test_non_dataclass_annotations_are_ignored_on_input():
    class SomeModel2(models.Model):
        name = models.CharField(max_length=255)

    class NonDataclass:
        non_dataclass_attr: str

    @dataclasses.dataclass
    class SomeDataclass:
        some_dataclass_attr: str

    @strawberry.input
    class SomeStrawberryInput:
        some_strawberry_attr: str

    @strawberry_django.input(SomeModel2)
    class SomeModelInput(SomeStrawberryInput, SomeDataclass, NonDataclass):
        name: str

    @strawberry.type
    class Query:
        @strawberry.field
        def some_field(self, my_input: SomeModelInput) -> str: ...

    schema = strawberry.Schema(query=Query)
    expected = """\
    type Query {
      someField(myInput: SomeModelInput!): String!
    }

    input SomeModelInput {
      someStrawberryAttr: String!
      someDataclassAttr: String!
      name: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


def test_optimizer_hints_on_type():
    class OtherModel(models.Model):
        name = models.CharField(max_length=255)

    class SomeModel3(models.Model):
        name = models.CharField(max_length=255)
        other = models.ForeignKey(OtherModel, on_delete=models.CASCADE)

    @strawberry_django.type(
        SomeModel3,
        only=["name", "other", "other_name"],
        select_related=["other"],
        prefetch_related=["other"],
        annotate={"other_name": models.F("other__name")},
    )
    class SomeModelType:
        name: str

    store = get_django_definition(SomeModelType, strict=True).store

    assert store.only == ["name", "other", "other_name"]
    assert store.select_related == ["other"]
    assert store.prefetch_related == ["other"]
    assert store.annotate == {"other_name": models.F("other__name")}


def test_custom_field_kept_on_inheritance():
    class SomeModel4(models.Model):
        foo = models.CharField(max_length=255)

    class CustomField(StrawberryDjangoField): ...

    @strawberry_django.type(SomeModel4)
    class SomeModelType:
        foo: strawberry.auto = CustomField()

    @strawberry_django.type(SomeModel4)
    class SomeModelSubclassType(SomeModelType): ...

    for type_ in [SomeModelType, SomeModelSubclassType]:
        object_definition = get_object_definition(type_, strict=True)
        field = object_definition.get_field("foo")
        assert isinstance(field, CustomField)
