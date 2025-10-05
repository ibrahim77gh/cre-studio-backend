from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.conf import settings
import tempfile
import os
import shutil

from .models import (
    PropertyGroup, Property, Campaign, CreativeAsset, 
    CampaignComment, CampaignCommentAttachment
)

User = get_user_model()


class FileDeletionTests(TestCase):
    """Test file deletion when models are deleted."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test property group and property
        self.property_group = PropertyGroup.objects.create(name='Test Group')
        self.property = Property.objects.create(
            name='Test Property',
            property_group=self.property_group
        )
        
        # Create test campaign
        self.campaign = Campaign.objects.create(
            property=self.property,
            user=self.user,
            center='Test Center'
        )
        
        # Create test comment
        self.comment = CampaignComment.objects.create(
            campaign=self.campaign,
            user=self.user,
            content='Test comment'
        )

    def tearDown(self):
        """Clean up test files."""
        # Clean up any remaining test files
        if hasattr(self, 'test_file_path') and os.path.exists(self.test_file_path):
            os.unlink(self.test_file_path)

    def test_creative_asset_file_deletion(self):
        """Test that CreativeAsset file is deleted when object is deleted."""
        # Create a temporary test file
        test_file = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        # Create CreativeAsset
        creative_asset = CreativeAsset.objects.create(
            campaign=self.campaign,
            file=test_file,
            asset_type='image'
        )
        
        # Get the file path
        file_path = creative_asset.file.path
        
        # Verify file exists
        self.assertTrue(os.path.exists(file_path))
        
        # Delete the CreativeAsset
        creative_asset.delete()
        
        # Verify file is deleted
        self.assertFalse(os.path.exists(file_path))

    def test_comment_attachment_file_deletion(self):
        """Test that CampaignCommentAttachment file is deleted when object is deleted."""
        # Create a temporary test file
        test_file = SimpleUploadedFile(
            "test_document.pdf",
            b"fake pdf content",
            content_type="application/pdf"
        )
        
        # Create CampaignCommentAttachment
        attachment = CampaignCommentAttachment.objects.create(
            comment=self.comment,
            file=test_file,
            original_filename='test_document.pdf',
            file_size=test_file.size,
            file_type='pdf'
        )
        
        # Get the file path
        file_path = attachment.file.path
        
        # Verify file exists
        self.assertTrue(os.path.exists(file_path))
        
        # Delete the CampaignCommentAttachment
        attachment.delete()
        
        # Verify file is deleted
        self.assertFalse(os.path.exists(file_path))

    def test_file_deletion_with_storage_api(self):
        """Test file deletion using Django's storage API."""
        # Create a temporary test file
        test_file = SimpleUploadedFile(
            "storage_test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        # Create CreativeAsset
        creative_asset = CreativeAsset.objects.create(
            campaign=self.campaign,
            file=test_file,
            asset_type='document'
        )
        
        # Get the file name (relative to media root)
        file_name = creative_asset.file.name
        
        # Verify file exists using storage API
        self.assertTrue(default_storage.exists(file_name))
        
        # Delete the CreativeAsset
        creative_asset.delete()
        
        # Verify file is deleted using storage API
        self.assertFalse(default_storage.exists(file_name))

    def test_multiple_assets_deletion(self):
        """Test that multiple files are deleted when multiple assets are deleted."""
        # Create multiple CreativeAssets
        assets = []
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"test_image_{i}.jpg",
                b"fake image content",
                content_type="image/jpeg"
            )
            asset = CreativeAsset.objects.create(
                campaign=self.campaign,
                file=test_file,
                asset_type='image'
            )
            assets.append(asset)
        
        # Verify all files exist
        file_paths = [asset.file.path for asset in assets]
        for file_path in file_paths:
            self.assertTrue(os.path.exists(file_path))
        
        # Delete all assets
        CreativeAsset.objects.filter(campaign=self.campaign).delete()
        
        # Verify all files are deleted
        for file_path in file_paths:
            self.assertFalse(os.path.exists(file_path))

    def test_cascade_deletion_with_files(self):
        """Test that files are deleted when parent objects are cascade deleted."""
        # Create CreativeAsset
        test_file = SimpleUploadedFile(
            "cascade_test.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        creative_asset = CreativeAsset.objects.create(
            campaign=self.campaign,
            file=test_file,
            asset_type='image'
        )
        
        # Create CommentAttachment
        comment_file = SimpleUploadedFile(
            "comment_attachment.pdf",
            b"fake pdf content",
            content_type="application/pdf"
        )
        attachment = CampaignCommentAttachment.objects.create(
            comment=self.comment,
            file=comment_file,
            original_filename='comment_attachment.pdf',
            file_size=comment_file.size,
            file_type='pdf'
        )
        
        # Get file paths
        asset_file_path = creative_asset.file.path
        attachment_file_path = attachment.file.path
        
        # Verify files exist
        self.assertTrue(os.path.exists(asset_file_path))
        self.assertTrue(os.path.exists(attachment_file_path))
        
        # Delete campaign (should cascade delete CreativeAsset and related comments/attachments)
        self.campaign.delete()
        
        # Verify CreativeAsset file is deleted
        self.assertFalse(os.path.exists(asset_file_path))
        
        # Verify CommentAttachment file is also deleted (due to cascade deletion of comment)
        self.assertFalse(os.path.exists(attachment_file_path))
