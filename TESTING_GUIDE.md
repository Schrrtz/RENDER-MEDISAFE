# Admin Features Testing Guide

## Quick Test Checklist

### Test 1: Forgot Password - Contact Method UI ✅
**File**: `/auth/forgot-password/`

1. Open forgot password modal
2. Go to Step 2 (after verification)
3. **Expected Results**:
   - ✅ Phone option has **GREEN border and background**
   - ✅ Phone option shows "SECURE - Password will be sent here"
   - ✅ Phone option shows phone numbers: **09685699664 / 88006290**
   - ✅ Phone option is **checked by default** (not email)
   - ✅ Email, Messenger, Facebook show "(Reference Only)"
   - ✅ Warning message at top: "Your new password will be sent to you via PHONE CALL ONLY for security"
   - ✅ All 4 contact options still selectable (for admin reference)

---

### Test 2: Edit User Button ✅
**Location**: Admin > User Management tab

1. Click any **Edit** button (first action button) on a user row
2. **Expected Results**:
   - ✅ Edit modal opens
   - ✅ All user fields populate correctly:
     - ID, Username, Email, Role
     - First Name, Middle Name, Last Name
     - Sex, Birthday
     - Contact Number, Contact Person, Address
     - Status (Active/Inactive)
   - ✅ Can modify any field
   - ✅ Can submit changes successfully
   - ✅ Modal closes after save
   - ✅ User list refreshes with updated data

---

### Test 3: Notification Bell ✅
**Location**: Admin Dashboard (ModDashboard)

1. Submit password reset request as a regular user
2. **Expected Results**:
   - ✅ Notification badge appears on bell icon
   - ✅ Badge shows count of unread notifications
   - ✅ Click bell icon to see dropdown panel
   - ✅ Password reset notification appears in list
   - ✅ Notification shows:
     - User's name and details
     - Contact preference selected
     - Timestamp
   - ✅ Click notification navigates to User Management
   - ✅ Click on notification marks it as read
   - ✅ Badge count decreases

---

### Test 4: View Password Reset Requests ✅
**Location**: Admin > User Management > User Actions

1. In User Management, click **View Password Reset Requests** button (3rd action, key icon)
2. **Expected Results**:
   - ✅ Modal opens showing "Password Reset Requests"
   - ✅ Displays loading state briefly
   - ✅ Shows list of password reset requests for that user with:
     - Request title
     - Request message
     - Date/time submitted
     - Priority badge (high/urgent/normal)
     - "ID Photo Attached" indicator (if file included)
   - ✅ **Download** button available if file attached
   - ✅ Can download user's ID photo
   - ✅ **Mark as Read** button to mark request as reviewed
   - ✅ Shows "No password reset requests" if none exist

---

### Test 5: End-to-End Flow ✅

#### Step 1: User Requests Password Reset
1. Go to login page
2. Click "Forgot Password"
3. Enter username or email - verification succeeds
4. Upload ID photo (optional)
5. Select contact method (should default to **Phone** with green highlight)
6. Submit request
7. See success message

#### Step 2: Admin Sees Notification
1. Admin logs in
2. Go to ModDashboard
3. **Expected**: 
   - ✅ Bell icon shows notification badge
   - ✅ Dropdown lists password reset notification
   - ✅ Notification shows requesting user's details

#### Step 3: Admin Views & Manages Request
1. Click on notification (goes to User Management)
2. Or navigate to User Management > Users tab
3. Find the user who requested reset
4. Click **View Password Reset Requests** (3rd button)
5. **Expected**:
   - ✅ Modal shows the request
   - ✅ Can download ID photo if provided
   - ✅ Can mark as read
6. Click **Edit** button (1st action) on same user
7. **Expected**:
   - ✅ Modal opens with user info
   - ✅ Can verify user details
   - ✅ Can update status if needed

---

## Common Issues & Troubleshooting

### Issue: Notification bell not showing badge
**Solution**:
1. Refresh the page
2. Check browser console for JavaScript errors
3. Verify admin user has proper role/permissions
4. Check that `is_admin` session variable is set

### Issue: Edit button not opening modal
**Solution**:
1. Check browser console for JavaScript errors
2. Verify button has `class="edit-user-btn"`
3. Verify button has all required `data-*` attributes
4. Clear browser cache and refresh

### Issue: Password reset requests modal showing error
**Solution**:
1. Check user_id in button matches actual user
2. Verify endpoint `/api/password-reset-requests/{user_id}/` is accessible
3. Check that password reset notifications were created
4. Verify file exists if "Download" button appears

### Issue: Contact method not showing phone as default
**Solution**:
1. Hard refresh page (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Check that modal HTML includes `checked` attribute on phone radio

### Issue: Green styling not appearing on phone option
**Solution**:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Refresh page
3. Verify CSS classes are loading: `border-green-300`, `bg-green-50`, `text-green-700`
4. Check that Tailwind CSS is properly compiled

---

## Performance Notes

- ✅ Notification bell updates every time page loads
- ✅ Lazy loads last 5 unread notifications (efficient)
- ✅ Edit modal populates instantly with local data
- ✅ Password reset requests modal has loading state while fetching
- ✅ File downloads use native browser download
- ✅ No blocking operations

---

## Security Notes

- ✅ All API endpoints require admin session (`is_admin`)
- ✅ CSRF tokens required on all POST requests
- ✅ File downloads verified before serving
- ✅ Password reset requests filtered by admin's view
- ✅ User data properly escaped in notifications
- ✅ No sensitive data in client-side storage

---

## Browser Compatibility

- ✅ Chrome/Chromium (Latest)
- ✅ Firefox (Latest)
- ✅ Safari (Latest)
- ✅ Edge (Latest)
- ✅ Mobile browsers

---

**All Systems Operational** ✅

If any issues are found during testing, check the browser console for JavaScript errors and the Django logs for backend errors.
