# Base Mini App Setup Guide

This document explains how to deploy and configure Glisk as a Base mini app (which is the same as a Farcaster mini app).

## What We've Done

✅ **Phase 1: Basic Integration (Completed)**

1. **Installed SDK**: Added `@farcaster/miniapp-sdk` package
2. **Added ready call**: Updated `src/App.tsx` to call `sdk.actions.ready()` on mount
3. **Created manifest**: Added `public/.well-known/farcaster.json` with app metadata
4. **Added embed metadata**: Updated `index.html` with `fc:miniapp` meta tag

## What You Need to Do Next

### Step 1: Deploy to Production

The app **must be publicly accessible via HTTPS** for Base mini app features to work. Localhost testing is not supported by the Base preview tool.

**Deployment checklist**:

- [ ] Build the app: `npm run build`
- [ ] Deploy to your hosting provider (current: glisk.xyz)
- [ ] Verify the manifest is accessible at: `https://glisk.xyz/.well-known/farcaster.json`
- [ ] Verify the app loads correctly in a browser

### Step 2: Generate Account Association

After deployment, you need to generate the `accountAssociation` fields in the manifest:

1. **Go to Base Build Account Association Tool**:

   - Visit: https://www.base.dev/preview?tab=account

2. **Submit your domain**:

   - Paste `glisk.xyz` in the domain field
   - Click "Submit"

3. **Verify ownership**:

   - Click the "Verify" button
   - Sign the message with your Base Account wallet
   - This proves you own both the domain and the wallet

4. **Copy the generated fields**:

   - After verification, you'll see three fields: `header`, `payload`, `signature`
   - Copy these values

5. **Update the manifest**:

   - Edit `public/.well-known/farcaster.json`
   - Replace the placeholder values in `accountAssociation`:
     ```json
     "accountAssociation": {
       "header": "PASTE_GENERATED_VALUE",
       "payload": "PASTE_GENERATED_VALUE",
       "signature": "PASTE_GENERATED_VALUE"
     }
     ```
   - Also update `baseBuilder.ownerAddress` with your Base Account address (the wallet you used for verification)

6. **Redeploy**:
   - Deploy the updated manifest to production
   - Verify it's accessible at `https://glisk.xyz/.well-known/farcaster.json`

### Step 3: Test in Base Preview

1. **Go to Base Build Preview Tool**:

   - Visit: https://www.base.dev/preview

2. **Test your mini app**:
   - The preview tool should detect your manifest automatically
   - Test the app launch
   - Verify the splash screen dismisses correctly
   - Check that the app functions as expected

### Step 4: Publish

Once testing is successful:

1. **Share in Base App**:

   - Post your app URL (`https://glisk.xyz`) in the Base app
   - The fc:miniapp meta tag will render a rich preview with a launch button

2. **Update manifest for production**:
   - Edit `public/.well-known/farcaster.json`
   - Change `"noindex": false` (currently set to `true` for testing)
   - This allows your app to be indexed in Base App search

## Configuration Reference

### Manifest File

Location: `public/.well-known/farcaster.json`

**Key fields you may want to customize**:

- `miniapp.name`: App name (max 32 chars) - currently "Glisk"
- `miniapp.subtitle`: Short description (max 30 chars) - currently "AI-Generated NFTs on Base"
- `miniapp.description`: Full description (max 170 chars)
- `miniapp.tagline`: Marketing tagline (max 30 chars)
- `miniapp.screenshotUrls`: Add app screenshots (max 3, portrait 1284×2778px)
- `miniapp.heroImageUrl`: Hero image for social sharing (1200×630px)
- `miniapp.noindex`: Set to `false` when ready for public indexing

**Optional enhancements**:

- Add screenshots to showcase the app
- Create a custom hero image for better social sharing
- Optimize icon and splash images for mini app display

### Embed Meta Tag

Location: `index.html`

The `fc:miniapp` meta tag controls how your app appears when shared:

```html
<meta
  name="fc:miniapp"
  content='{
  "version":"next",
  "imageUrl":"https://glisk.xyz/android-chrome-512x512.png",
  "button":{
    "title":"Open Glisk",
    "action":{
      "type":"launch_miniapp",
      "name":"Glisk",
      "url":"https://glisk.xyz"
    }
  }
}'
/>
```

## Understanding Base Mini Apps

### Key Concepts

- **Base mini apps = Farcaster mini apps**: They use the same protocol and SDK
- **Base App** is built on top of Farcaster, so compatibility is automatic
- **Authentication** uses Farcaster identity (FID = Farcaster ID)
- **Your existing stack works**: OnchainKit, Wagmi, RainbowKit are fully compatible

### What the SDK Provides

```typescript
import { sdk } from '@farcaster/miniapp-sdk'

// 1. Signal app is ready (required - already implemented in App.tsx)
await sdk.actions.ready()

// 2. Get authentication token (optional - for future enhancement)
const { token } = await sdk.quickAuth.getToken()

// 3. Make authenticated API calls (optional)
const response = await sdk.quickAuth.fetch(`${API_URL}/endpoint`, {
  headers: { Authorization: `Bearer ${token}` },
})

// 4. Access user context (optional - not cryptographically verified)
const context = sdk.context // Contains user.displayName, etc.
```

### Future Enhancements (Optional)

Consider adding in Phase 2:

1. **Quick Auth Integration**:

   - Use Farcaster's Quick Auth for authentication
   - Returns JWT with Farcaster ID (FID)
   - Can replace or complement existing wallet connection

2. **Social Features**:

   - Access user's Farcaster social graph
   - Show friends who also use Glisk
   - Recommend creators based on social connections

3. **Notifications**:

   - Implement webhook to receive notification events
   - Push notifications for NFT mints, creator updates, etc.

4. **Enhanced Sharing**:
   - Use `sdk.actions.shareUrl()` to share minted NFTs
   - Optimize share previews with better images

## Troubleshooting

### Manifest Not Found

**Symptom**: Base preview tool can't find manifest at `/.well-known/farcaster.json`

**Solution**:

1. Verify the file exists in `public/.well-known/farcaster.json`
2. Build and deploy: `npm run build`
3. Test in browser: `https://glisk.xyz/.well-known/farcaster.json`
4. Check Vite config doesn't exclude `.well-known` directory

### App Not Launching

**Symptom**: Base preview shows loading screen forever

**Solution**:

1. Verify `sdk.actions.ready()` is called in `App.tsx` (already implemented)
2. Check browser console for errors
3. Verify SDK is installed: `npm list @farcaster/miniapp-sdk`

### Account Association Fails

**Symptom**: Can't verify domain ownership

**Solution**:

1. Ensure app is deployed and accessible via HTTPS
2. Use the wallet that owns the Base Account
3. Clear browser cache and try again
4. Verify you're on the correct network (Base Mainnet)

### Invalid Manifest Format

**Symptom**: Base preview tool reports JSON errors

**Solution**:

1. Validate JSON: `cat public/.well-known/farcaster.json | jq .`
2. Check for missing commas, quotes, or brackets
3. Verify all URLs use HTTPS
4. Ensure required fields are present

## Resources

- **Base Mini Apps Docs**: https://docs.base.org/mini-apps/
- **Migration Guide**: https://docs.base.org/mini-apps/quickstart/migrate-existing-apps
- **Build Checklist**: https://docs.base.org/mini-apps/quickstart/build-checklist
- **Base Build Preview Tool**: https://www.base.dev/preview
- **Farcaster SDK Docs**: https://docs.farcaster.xyz/developers/frames/miniapps

## Summary

Your Glisk app is now configured as a Base mini app! The code changes are minimal and non-breaking:

✅ SDK installed and initialized
✅ Manifest created with app metadata
✅ Embed meta tag added for social sharing
✅ Ready call implemented to dismiss splash screen

**Next steps**: Deploy → Generate account association → Test → Publish
