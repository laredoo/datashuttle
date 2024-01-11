import os.path
import shutil

import pytest
from base import BaseTest

from datashuttle.utils import formatting
from datashuttle.utils.custom_exceptions import NeuroBlueprintError


class TestFormatting(BaseTest):
    @pytest.mark.parametrize("prefix", ["sub", "ses"])
    @pytest.mark.parametrize(
        "input", [1, {"test": "one"}, 1.0, ["1", "2", ["three"]]]
    )
    def test_format_names_bad_input(self, input, prefix):
        """
        Test that names passed in incorrect type
        (not str, list) raise appropriate error.
        """
        with pytest.raises(TypeError) as e:
            formatting.format_names(input, prefix)

        assert f"Ensure {prefix} names are a list of strings." == str(e.value)

    @pytest.mark.parametrize("prefix", ["sub", "ses"])
    def test_format_names_duplicate_ele(self, prefix):
        """
        Test that appropriate error is raised when duplicate name
        is passed to format_names().
        """
        with pytest.raises(NeuroBlueprintError) as e:
            formatting.check_and_format_names(
                ["1", "2", "3", "3", "4"], prefix
            )

        assert (
            f"{prefix} names must all have unique integer "
            f"ids after the {prefix} prefix." == str(e.value)
        )

    def test_format_names_prefix(self):
        """
        Check that format_names correctly prefixes input
        with default sub or ses prefix. This is less useful
        now that ses/sub name dash and underscore order is
        more strictly checked.
        """
        prefix = "sub"

        # check name is prefixed
        formatted_names = formatting.format_names(["1"], prefix)
        assert formatted_names[0] == "sub-1"

        # check existing prefix is not duplicated
        formatted_names = formatting.format_names(["sub-1"], prefix)
        assert formatted_names[0] == "sub-1"

        # test mixed list of prefix and unprefixed are prefixed correctly.
        mixed_names = ["1", prefix + "-four", "5", prefix + "-6"]
        formatted_names = formatting.format_names(mixed_names, prefix)
        assert formatted_names == [
            "sub-1",
            "sub-four",
            "sub-5",
            "sub-6",
        ]

    def test_warning_non_consecutive_numbers(self, project):
        project.make_folders(
            ["sub-01", "sub-02", "sub-04"], ["ses-05", "ses-10"]
        )

        with pytest.warns(UserWarning) as w:
            project.get_next_sub_number()
        assert (
            str(w[0].message) == "A subject number has been skipped, "
            "currently used subject numbers are: [1, 2, 4]"
        )

        with pytest.warns(UserWarning) as w:
            project.get_next_ses_number("sub-02")
        assert (
            str(w[0].message)
            == "A subject number has been skipped, currently "
            "used subject numbers are: [5, 10]"
        )

    # ----------------------------------------------------------------------------------
    # Inconsistent sub or ses value lengths
    # ----------------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "sub_name",
        ["sub-001", "sub-001_@DATE@", "sub-001_random-tag_another-tag"],
    )
    @pytest.mark.parametrize(
        "bad_sub_name",
        [
            "sub-3",
            "sub-01",
            "sub-0001",
            "sub-07_@DATE@",
            "sub-1321",
            "sub-22",
            "sub-234234453_@DATETIME@",
        ],
    )
    def test_warn_on_inconsistent_sub_value_lengths(
        self, project, sub_name, bad_sub_name
    ):
        """
        This test checks that inconsistent sub value lengths are properly
        detected across the project. This is performed with an assortment
        of possible filenames and leading zero conflicts.

        These conflicts are detected across the project (i.e. if you have sub-03
        in remote and sub-004 in local, a warning should be shown). Therefore
        this function tests every combination of conflict across local and central).

        Note SSH version is not tested, but the core functionality detecting
        inconsistent leading zeros is agnostic to SSH, and SSH file searching
        is tested elsewhere.
        """
        # First make conflicting leading zero subject names in the local repo
        os.makedirs(project.cfg["local_path"] / "rawdata" / sub_name)
        os.makedirs(project.cfg["local_path"] / "rawdata" / bad_sub_name)
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "sub")

        # Now, have conflicting subject names, but one in local and one in central
        new_central_path = (
            project.cfg["local_path"].parent / "central" / project.project_name
        )
        os.makedirs(new_central_path, exist_ok=True)

        project.update_config_file(central_path=new_central_path)
        os.makedirs(project.cfg["central_path"] / "rawdata" / bad_sub_name)
        shutil.rmtree(project.cfg["local_path"] / "rawdata" / bad_sub_name)
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "sub")

        # Have conflicting subject names both in central.
        shutil.rmtree(project.cfg["local_path"] / "rawdata" / sub_name)
        os.makedirs(project.cfg["central_path"] / "rawdata" / sub_name)
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "sub")

    @pytest.mark.parametrize(
        "ses_name",
        ["ses-01", "ses-01_@DATE@", "ses-01_random-tag_another-tag"],
    )
    @pytest.mark.parametrize(
        "bad_ses_name",
        [
            "ses-3",
            "ses-001",
            "ses-0001",
            "ses-007_@DATE@",
            "ses-1453_@DATETIME@",
            "ses-234234234",
        ],
    )
    def test_warn_on_inconsistent_ses_value_lengths(
        self, project, ses_name, bad_ses_name
    ):
        """
        This function is exactly the same as `test_warn_on_inconsistent_sub_value_lengths()`
        but operates at the session level. This is extreme code duplication, but
        factoring the main logic out got very messy and hard to follow.
        So, in this case code duplicate is the price to pay.
        """
        # Have conflicting session names (in different subject directories)
        # on the local filesystem
        os.makedirs(
            project.cfg["local_path"] / "rawdata" / "sub-001" / ses_name
        )
        os.makedirs(
            project.cfg["local_path"] / "rawdata" / "sub-002" / bad_ses_name
        )
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "ses")

        # Now, have conflicting session names (in different subject directories)
        # where one subject directory is local and the other is central.
        new_central_path = (
            project.cfg["local_path"].parent / "central" / project.project_name
        )
        os.makedirs(new_central_path, exist_ok=True)

        project.update_config_file(central_path=new_central_path)
        os.makedirs(
            project.cfg["central_path"] / "rawdata" / "sub-001" / bad_ses_name
        )
        shutil.rmtree(project.cfg["local_path"] / "rawdata" / "sub-002")
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "ses")

        # Test the case where conflicting session names are both on central.
        shutil.rmtree(project.cfg["local_path"] / "rawdata" / "sub-001")
        os.makedirs(
            project.cfg["central_path"] / "rawdata" / "sub-001" / ses_name
        )
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "ses")

    def test_warn_on_inconsistent_sub_and_ses_value_lengths(self, project):
        """
        Test that warning is shown for both subject and session when
        inconsistent zeros are found in both.
        """
        os.makedirs(
            project.cfg["local_path"] / "rawdata" / "sub-001" / "ses-01"
        )
        os.makedirs(
            project.cfg["local_path"] / "rawdata" / "sub-03" / "ses-002"
        )
        self.check_inconsistent_sub_or_ses_value_length_warning(project, "sub")
        self.check_inconsistent_sub_or_ses_value_length_warning(
            project, "ses", warn_idx=1
        )

    def check_inconsistent_sub_or_ses_value_length_warning(
        self, project, sub_or_ses, warn_idx=0
    ):
        """"""
        with pytest.warns(UserWarning) as w:
            formatting.warn_on_inconsistent_sub_or_ses_value_lengths(
                project.cfg
            )

        assert (
            str(w[warn_idx].message) == f"Inconsistent value lengths for the "
            f"{sub_or_ses} key in the project found. It is "
            f"crucial these are made consistent as "
            f"soon as possible to avoid unexpected "
            f"behaviour of DataShuttle during data transfer."
        )
