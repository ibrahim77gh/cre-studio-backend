# Campaign Budget API Guide

## Overview
The new flexible campaign budget system allows you to manage budgets across multiple advertising platforms (Meta, Google Display, YouTube, OTT, etc.) with automatic net calculations.

## API Endpoints

### 1. Platform Management

#### Get All Platforms
```http
GET /api/platforms/
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "meta",
    "display_name": "Meta Ads",
    "net_rate": "0.8500",
    "is_active": true
  },
  {
    "id": 2,
    "name": "google_display",
    "display_name": "Google Display", 
    "net_rate": "0.8500",
    "is_active": true
  },
  {
    "id": 3,
    "name": "youtube",
    "display_name": "YouTube",
    "net_rate": "0.8500", 
    "is_active": true
  },
  {
    "id": 4,
    "name": "ott",
    "display_name": "OTT",
    "net_rate": "0.8500",
    "is_active": true
  }
]
```

### 2. Campaign Budget Management

#### Get Campaign with Budget
```http
GET /api/campaigns/{campaign_id}/
```
**Response:**
```json
{
    "id": 1,
    "property": 1,
    "user": 10,
    "pmcb_form_data": {
        "email": "syedibrahim4091@gmail.com",
        "fullName": "Syed Ibrahim",
        "centerName": "Derby Street",
        "keyEvent": "Santa Photos",
        "primaryGoal": "growEmailSubscribers",
        "targetAudience": "women 20 - 60 yrs old within 20 miles of FVM",
        "timeframe": "",
        "budget": "$5000, 50% of that for Google Display and 50% for Meta BUDGET",
        "platforms": [
            "googleDisplay",
            "metaFacebookInstagram"
        ],
        "creativeContext": "USE THE LOGO I HAVE GIVEN",
        "creativePlan": "Make sure the plan is achieved",
        "messaging": "Make reservations",
        "relevantLinks": "https://youtube.com",
        "additionalNotes": "TESTING NOTES",
        "start_date": "2025-10-14",
        "end_date": "2025-10-28"
    },
    "center": "Santa Photos & Holiday Shopping",
    "start_date": "2025-10-14",
    "end_date": "2025-10-28",
    "meta_main_copy_options": [
        "Make reservations for Santa photos and festive shopping all in one place.\nIdeal for women 25–65 within 20 miles of FVM—book your visit today!",
        "Skip the lines—secure your Santa shot and holiday gifts now.\nOpen to women 25–65 within 20 miles of FVM. Reserve your slot and shop with ease.",
        "Bring the kids and your list: Santa photos plus holiday finds.\nReservations open for women 25–65 within 20 miles of FVM. Book your slot today!",
        "Capture a magical Santa moment while you browse our festive collection.\nWomen 25–65 within 20 miles of FVM: book now and drive foot traffic to local shops.",
        "**Create memories with Santa while you shop local gifts. Reserve your spot today—within 20 miles of FVM. Limited slots!**"
    ],
    "meta_headline": [
        "Reserve Your Santa Photo Today",
        "Book Santa Photos & Holiday Shopping",
        "Snag Your Santa Moment This Season",
        "Meet Santa, Shop &amp; Smile—**<u>Book Now</u>**",
        "**Reserve Santa Visits & Shop Local - A Great Opportunity!**"
    ],
    "meta_desktop_display_copy": "Reserve your Santa photo slot and dive into holiday shopping—two festive experiences in one stop. This campaign targets women 25–65 within 20 miles of FVM and is designed to drive foot traffic to local retailers. Bring the family, browse gifts, and capture memories. **Book your visit today! and GET READY**",
    "meta_website_url": null,
    "meta_call_to_action": "Book Now",
    "meta_notes": "",
    "meta_ready": "false",
    "google_headlines": [
        "Santa Photo Season Today Store",
        "Women Photo Season Today Store",
        "Women Gifts Season Today Store",
        "**Women Gifts Nearby Today Toy shop**",
        "Girls Gifts Season Today Store"
    ],
    "google_long_headline": [
        "<u>Reserve Santa Photos and Shop Holiday Deals Nearby within 20 Miles of FVM for Easy Family Fun Now</u>",
        "**Make Reservations for Santa Photos and Holiday Shopping Nearby Within 20 Miles of FVM Now.**",
        "Secure Your Santa Photo Visit and Enjoy Holiday Shopping Nearby Within 20 Miles of FVM Now"
    ],
    "google_descriptions": [
        "Make reservations for Santa photos and holiday shopping and bring the family in today now.",
        "Reserve a Santa photo slot and enjoy a complete holiday shopping experience near you today",
        "Nearby Season Santa photo with shops gifts women girls dream group guide weeks store today and get now",
        "Nearby Trendy Santa photo gifts women girls dream group guide weeks shop today shops today",
        "Santa Photo Today Shops Gifts Women Girls Dream Plans Treat Local Gifts Today Shops Season"
    ],
    "google_website_url": null,
    "google_notes": "",
    "google_ready": "false",
    "dms_sync_ready": false,
    "approval_status": "pending",
    "ai_processing_status": "completed",
    "ai_processing_error": null,
    "ai_processed_at": "2025-10-04T11:36:36.545477Z",
    "created_at": "2025-10-04T11:32:51.033806Z",
    "updated_at": "2025-10-11T15:58:31.678854Z",
    "creative_assets_list": [
        {
            "id": 20,
            "campaign": 1,
            "file": "http://127.0.0.1:8000/media/campaign_assets/eric-brehm-JVQ7ElHJj9w-unsplash_1.jpg",
            "file_url": "http://127.0.0.1:8000/media/campaign_assets/eric-brehm-JVQ7ElHJj9w-unsplash_1.jpg",
            "file_name": "eric-brehm-JVQ7ElHJj9w-unsplash_1.jpg",
            "file_size": 6173753,
            "uploaded_at": "2025-10-10T09:50:49.928693Z",
            "asset_type": null,
            "platform_type": null
        },
        {
            "id": 21,
            "campaign": 1,
            "file": "http://127.0.0.1:8000/media/campaign_assets/cre-studio-logo.png",
            "file_url": "http://127.0.0.1:8000/media/campaign_assets/cre-studio-logo.png",
            "file_name": "cre-studio-logo.png",
            "file_size": 569593,
            "uploaded_at": "2025-10-10T09:52:44.580687Z",
            "asset_type": "image",
            "platform_type": "creative"
        }
    ],
    "campaign_dates": [],
    "budget": {
        "id": 2,
        "campaign": 1,
        "creative_charges_deductions": 150.0,
        "total_gross": 1200.0,
        "total_net": 615.0,
        "platform_budgets": [
            {
                "id": 1,
                "platform": {
                    "id": 1,
                    "name": "meta",
                    "display_name": "Meta Ads",
                    "net_rate": 0.85,
                    "is_active": true
                },
                "gross_amount": 200.0,
                "net_amount": 170.0
            },
            {
                "id": 2,
                "platform": {
                    "id": 2,
                    "name": "google_display",
                    "display_name": "Google Display",
                    "net_rate": 0.85,
                    "is_active": true
                },
                "gross_amount": 300.0,
                "net_amount": 255.0
            },
            {
                "id": 4,
                "platform": {
                    "id": 4,
                    "name": "ott",
                    "display_name": "OTT",
                    "net_rate": 0.85,
                    "is_active": true
                },
                "gross_amount": 400.0,
                "net_amount": 340.0
            }
        ],
        "meta_gross": 200.0,
        "meta_net": 170.0,
        "display_gross": 300.0,
        "display_net": 255.0
    }
}
```

#### Update Campaign Budget (Method 1: Update entire campaign)
```http
PATCH /api/campaigns/{campaign_id}/
Content-Type: application/json

{
  "budget": {
    "creative_charges_deductions": "150.00",
    "total_gross": "1200.00",
    "platform_budgets": [
      {
        "platform_id": 1,
        "gross_amount": "600.00"
      },
      {
        "platform_id": 2,
        "gross_amount": "400.00"
      },
      {
        "platform_id": 3,
        "gross_amount": "200.00"
      }
    ]
  }
}
```

#### Update Campaign Budget (Method 2: Direct budget endpoint)
```http
PATCH /api/campaigns/{campaign_id}/budget/
Content-Type: application/json

{
  "creative_charges_deductions": "150.00",
  "total_gross": "1200.00",
  "platform_budgets": [
    {
      "platform_id": 1,
      "gross_amount": "600.00"
    },
    {
      "platform_id": 2,
      "gross_amount": "400.00"
    },
    {
      "platform_id": 3,
      "gross_amount": "200.00"
    }
  ]
}
```

### 3. Platform-Specific Budget Updates

#### Update Single Platform Budget
```http
PATCH /api/campaigns/{campaign_id}/budget/platform/{platform_id}/
Content-Type: application/json

{
  "gross_amount": "750.00"
}
```

#### Add New Platform to Campaign
```http
POST /api/campaigns/{campaign_id}/budget/platforms/
Content-Type: application/json

{
  "platform_id": 4,
  "gross_amount": "300.00"
}
```

## Key Features

### 1. Automatic Net Calculation
- **Net Amount** = Gross Amount × Platform Net Rate
- **Total Net** = Sum of all platform net amounts - Creative charges deductions
- Net amounts are read-only and calculated automatically

### 2. Platform Flexibility
- Add new platforms without code changes
- Each platform can have different net rates
- Platforms can be activated/deactivated

### 3. Backward Compatibility
- Existing API calls using `meta_gross`, `meta_net`, etc. still work
- Frontend can gradually migrate to new structure

## Frontend Integration Examples

### React/Vue.js Example
```javascript
// Update campaign budget
const updateCampaignBudget = async (campaignId, budgetData) => {
  const response = await fetch(`/api/campaigns/${campaignId}/budget/`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      total_gross: budgetData.totalGross,
      creative_charges_deductions: budgetData.creativeCharges,
      platform_budgets: budgetData.platforms.map(platform => ({
        platform_id: platform.id,
        gross_amount: platform.grossAmount
      }))
    })
  });
  
  return response.json();
};

// Get available platforms
const getPlatforms = async () => {
  const response = await fetch('/api/platforms/');
  return response.json();
};
```

### Form Handling Example
```javascript
// Dynamic platform budget form
const PlatformBudgetForm = ({ campaign, onUpdate }) => {
  const [platforms, setPlatforms] = useState([]);
  const [budgetData, setBudgetData] = useState({
    total_gross: campaign.budget?.total_gross || 0,
    creative_charges_deductions: campaign.budget?.creative_charges_deductions || 0,
    platform_budgets: []
  });

  useEffect(() => {
    // Load available platforms
    getPlatforms().then(setPlatforms);
    
    // Initialize platform budgets
    const existingBudgets = campaign.budget?.platform_budgets || [];
    setBudgetData(prev => ({
      ...prev,
      platform_budgets: existingBudgets
    }));
  }, [campaign]);

  const updatePlatformBudget = (platformId, grossAmount) => {
    setBudgetData(prev => ({
      ...prev,
      platform_budgets: prev.platform_budgets.map(pb => 
        pb.platform_id === platformId 
          ? { ...pb, gross_amount: grossAmount }
          : pb
      ).concat(
        // Add new platform if not exists
        prev.platform_budgets.some(pb => pb.platform_id === platformId) 
          ? [] 
          : [{ platform_id: platformId, gross_amount: grossAmount }]
      )
    }));
  };

  const handleSubmit = () => {
    updateCampaignBudget(campaign.id, budgetData).then(onUpdate);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input 
        type="number"
        value={budgetData.total_gross}
        onChange={(e) => setBudgetData(prev => ({
          ...prev,
          total_gross: parseFloat(e.target.value)
        }))}
        placeholder="Total Gross Budget"
      />
      
      {platforms.map(platform => (
        <div key={platform.id}>
          <label>{platform.display_name}</label>
          <input
            type="number"
            value={budgetData.platform_budgets.find(pb => pb.platform_id === platform.id)?.gross_amount || 0}
            onChange={(e) => updatePlatformBudget(platform.id, parseFloat(e.target.value))}
            placeholder={`${platform.display_name} Gross Amount`}
          />
          <span>
            Net: {(budgetData.platform_budgets.find(pb => pb.platform_id === platform.id)?.gross_amount || 0) * platform.net_rate}
          </span>
        </div>
      ))}
      
      <button type="submit">Update Budget</button>
    </form>
  );
};
```

## Migration Strategy

### Phase 1: Backend Ready (Current)
- ✅ New models and serializers implemented
- ✅ Backward compatibility maintained
- ✅ Migration commands available

### Phase 2: Frontend Updates
1. Update budget forms to use platform_budgets array
2. Add platform selection/management UI
3. Update budget display components
4. Test with new structure

### Phase 3: Cleanup
1. Remove backward compatibility fields
2. Update API documentation
3. Remove old migration commands

## Database Queries

### Get Campaign with All Platform Budgets
```python
campaign = Campaign.objects.select_related('budget').prefetch_related(
    'budget__platform_budgets__platform'
).get(id=campaign_id)
```

### Calculate Total Budget
```python
budget = CampaignBudget.objects.get(campaign_id=campaign_id)
total_gross = budget.total_gross
total_net = budget.total_net  # Auto-calculated
```

### Get Platform Budget
```python
platform_budget = PlatformBudget.objects.get(
    campaign_budget__campaign_id=campaign_id,
    platform__name='meta'
)
gross = platform_budget.gross_amount
net = platform_budget.net_amount  # Auto-calculated
```

This new structure provides maximum flexibility while maintaining backward compatibility during the transition period.
