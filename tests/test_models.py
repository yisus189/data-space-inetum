import pytest
from src.models.user import User, Role, UserRole
from src.models.publication import Publication, PublicationStatus


def test_create_user(db_session, sample_user_data):
    """Test creating a user"""
    user = User(**sample_user_data)
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.username == sample_user_data["username"]
    assert user.email == sample_user_data["email"]
    assert user.roles == sample_user_data["roles"]


def test_create_role(db_session):
    """Test creating a role"""
    role = Role(
        name="test_role",
        description="A test role",
        permissions=["read", "write"]
    )
    db_session.add(role)
    db_session.commit()
    
    assert role.id is not None
    assert role.name == "test_role"
    assert role.permissions == ["read", "write"]


def test_create_publication(db_session, sample_user_data, sample_publication_data):
    """Test creating a publication"""
    # Create user first
    user = User(**sample_user_data)
    db_session.add(user)
    db_session.commit()
    
    # Create publication
    publication = Publication(
        **sample_publication_data,
        publisher_id=user.id
    )
    db_session.add(publication)
    db_session.commit()
    
    assert publication.id is not None
    assert publication.title == sample_publication_data["title"]
    assert publication.publisher_id == user.id
    assert publication.status == PublicationStatus.DRAFT


def test_user_publications_relationship(db_session, sample_user_data, sample_publication_data):
    """Test user-publications relationship"""
    user = User(**sample_user_data)
    db_session.add(user)
    db_session.commit()
    
    # Create multiple publications
    for i in range(3):
        pub = Publication(
            title=f"Publication {i}",
            description=f"Description {i}",
            publisher_id=user.id
        )
        db_session.add(pub)
    db_session.commit()
    
    # Verify relationship
    assert len(user.publications) == 3
    assert all(pub.publisher_id == user.id for pub in user.publications)
