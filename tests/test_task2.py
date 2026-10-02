"""
Tests for Task 2 — dimension, color, material extraction.

Cases are drawn from real data (sampled from sales.xlsx).
"""

import pytest
from src.task2_extraction import extract_dimension, extract_colors, extract_materials


# ---------------------------------------------------------------------
# DIMENSION
# ---------------------------------------------------------------------
class TestDimension:
    def test_simple_2d(self):
        assert extract_dimension("Matelas mousse 140x190 cm") == {
            "dimension": "140x190",
            "unit": "cm",
        }

    def test_2d_no_space_before_unit(self):
        assert extract_dimension("Tapis deco rectangle salou 45x120cm") == {
            "dimension": "45x120",
            "unit": "cm",
        }

    def test_2d_uppercase_x(self):
        assert extract_dimension("Couette 240X220 cm") == {
            "dimension": "240x220",
            "unit": "cm",
        }

    def test_2d_with_spaces(self):
        assert extract_dimension("Matelas bain de soleil 60 x 190 cm") == {
            "dimension": "60x190",
            "unit": "cm",
        }

    def test_3d_plain(self):
        assert extract_dimension("Cadre photo 10x15x2 cm") == {
            "dimension": "10x15x2",
            "unit": "cm",
        }

    def test_3d_labeled(self):
        assert extract_dimension("Table L 110 x P 60 x H 36 cm") == {
            "dimension": "110x60x36",
            "unit": "cm",
        }

    def test_single_with_unit(self):
        assert extract_dimension("Meuble haut 80 cm 2 portes") == {
            "dimension": "80",
            "unit": "cm",
        }

    def test_mm_unit(self):
        assert extract_dimension("Roues 260mm") == {
            "dimension": "260",
            "unit": "mm",
        }

    def test_no_dimension_lot(self):
        assert extract_dimension("Lot de 2 tables basses") is None

    def test_no_dimension_count(self):
        assert extract_dimension("Bibliotheque 3 niveaux") is None

    def test_no_dimension_usb(self):
        assert extract_dimension("Alpexe usb 3 0 vers sata") is None

    def test_none_input(self):
        assert extract_dimension(None) is None

    def test_empty_string(self):
        assert extract_dimension("") is None


# ---------------------------------------------------------------------
# COLORS
# ---------------------------------------------------------------------
class TestColors:
    def test_single_color(self):
        assert extract_colors("Lit coffre blanc") == ["blanc"]

    def test_two_colors(self):
        result = extract_colors("Fauteuil patchwork bleu et gris")
        assert "bleu" in result and "gris" in result

    def test_feminine_plural(self):
        assert "blanc" in extract_colors("Lot de 2 tables blanches")

    def test_wood_tone_as_color(self):
        assert "chene" in extract_colors("Table basse chene sonoma")

    def test_multiword_color(self):
        assert "gris anthracite" in extract_colors("Meuble gris anthracite")

    def test_no_color(self):
        assert extract_colors("Table basse carree") == []

    def test_accent_insensitive(self):
        assert "dore" in extract_colors("Lampadaire dore")

    def test_none_input(self):
        assert extract_colors(None) == []

    def test_empty_string(self):
        assert extract_colors("") == []


# ---------------------------------------------------------------------
# MATERIALS
# ---------------------------------------------------------------------
class TestMaterials:
    def test_simple_material(self):
        assert "mousse" in extract_materials("Matelas mousse 140x190 cm")

    def test_mdf(self):
        assert "mdf" in extract_materials("Table en MDF noir")

    def test_pvc(self):
        assert "pvc" in extract_materials("Lit coffre miami pvc blanc")

    def test_no_material(self):
        assert extract_materials("Table basse carree") == []

    def test_none_input(self):
        assert extract_materials(None) == []

    def test_empty_string(self):
        assert extract_materials("") == []