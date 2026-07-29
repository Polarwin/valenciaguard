# ValenciaGuard — User Manual (English)

> For the three roles: **superuser** (agency boss), **employee** (property manager / admin) and **owner**.
> System URL: https://valenciaguard.duckdns.org/

---

## 1. Common tasks (all roles)

### Sign in
1. Open https://valenciaguard.duckdns.org/ — you will be redirected to the login page.
2. Enter the username and password given to you by the superuser or a staff member.
3. Forgot your password? Ask an administrator to reset it; the new password is shown only once.

### Switch language
Top right of every page (bottom of the login page): **ES | EN | 中文**. The app remembers your choice.

### Install as a phone app
- **Android (Chrome)**: open the site → menu (three dots) → "Add to Home screen".
- **iPhone (Safari)**: open the site → Share button → "Add to Home Screen".

A blue "VG" icon appears; the app opens full-screen without the browser UI.

---

## 2. Superuser (agency boss)

You have every staff feature (section 3) plus **employee account management**:

### Create employee accounts
1. Go to **Users**.
2. In "Add user": enter a username, choose the **admin** role, and set an initial password (the "generate" button creates a strong one).
3. Pass the credentials to the employee and ask them to change the password soon.

### Reset / delete accounts
- You can reset anyone's password from the user list (shown once).
- You can delete employee and owner accounts; **you cannot delete yourself**, so at least one superuser always exists.

> Only you can create, reset or delete **employee (admin)** accounts; staff cannot manage other staff.

---

## 3. Employee (property manager / admin)

After signing in, the top navigation offers:

| Feature | What it's for |
|---|---|
| **Dashboard** | Property count, occupancy, month/YTD collections, overdue rent, upcoming alerts, open issues |
| **Properties** | Add/edit/delete properties; each property page manages tenant, contract, rent records, documents, issues |
| **Calendar** | Key dates: contract end, notice deadline, rent update, insurance expiry, rent due |
| **Owners** | Owner records (name, email, phone, WeChat, notes) |
| **Users** | Create login accounts for **owners** (role owner, linkable to their record) and reset their passwords |
| **Rent calculator** | Maximum legal rent increase under the IRAV index |
| **AI assistant** | LAU questions, drafting tenant letters in Spanish, translating vendor quotes into Chinese |
| **Settings** | Company name, notification email, cost threshold, IRAV rate, and the audit log |

### Everyday workflows
1. **New owner**: add their record under Owners → create an owner account under Users (role owner, linked) → send them the credentials.
2. **New property**: Properties → New → add tenant and contract on the property page. LAU dates (mandatory period, notice deadline, next rent update) are computed automatically.
3. **Rent tracking**: on the property page, add each month's rent record and mark it paid when the money arrives.
4. **Issues**: when a tenant reports a problem, create an issue; the AI suggests urgency, liability (landlord/tenant) and a Spanish draft reply. Costs above the threshold need owner approval.
5. **Documents**: upload contracts, deposit receipts and insurance policies on the property page; the system tries to extract key contract data automatically.

---

## 4. Owner

Owners land on the **owner portal** (available in 中文, ES and EN):

### Home
- Summary cards: properties, this month's rent, occupancy, pending issues.
- "My properties" list with a **View details** link per property.

### Property detail
- **Contract status**: type, start date, monthly rent, and a countdown of key dates (days left / days overdue).
- **Rent records**: monthly amount due, amount paid, status (paid / pending / late).
- **Issues**: reported problems for that property and their progress.
- **Documents**: contracts and insurance policies, downloadable.
- **Monthly report**: the **"Download monthly report (PDF)"** button generates a Chinese-language report, ready to save or forward.

### What owners cannot do
Owners can only **view** their own properties, rents, issues and documents; they cannot edit data or see other owners' information. For any change (new repair, new contract), contact the agency staff.

---

## 5. Security tips

- Change initial passwords (e.g. admin123) as soon as possible.
- Never share accounts: every employee and every owner should have their own, so the audit log stays meaningful.
- Passwords need at least 8 characters; use the "generate" button for random ones.
