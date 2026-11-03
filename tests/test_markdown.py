from robot_knowledgebase.ingest.markdown import load_markdown


def test_load_markdown_parses_front_matter_and_title(tmp_path):
    path = tmp_path / "guide.md"
    path.write_text(
        "---\ntitle: Lidar Setup\ncategory: sensors\ntags: [lidar, ros2]\n"
        "published: true\n---\n# Setup\n\nConnect the sensor.\n",
        encoding="utf-8",
    )

    document = load_markdown(path)

    assert document.title == "Lidar Setup"
    assert document.metadata["category"] == "sensors"
    assert document.metadata["tags"] == ["lidar", "ros2"]
    assert document.metadata["published"] is True
    assert document.content.startswith("# Setup")
    assert document.source == path.as_posix()


def test_load_markdown_uses_heading_without_front_matter(tmp_path):
    path = tmp_path / "guide.md"
    path.write_text("# Navigation Guide\n\nBody", encoding="utf-8")

    document = load_markdown(path)

    assert document.title == "Navigation Guide"
    assert document.metadata["category"] == "general"
