const { Firestore } = require('@google-cloud/firestore');

// This will automatically use the GOOGLE_APPLICATION_CREDENTIALS
// environment variable (set by Render) to find the key file.
const db = new Firestore();
const keysCollection = db.collection('api_keys');

console.log("Connected to Google Firestore.");

/**
 * Validates an API key against the database.
 * @param {string} apiKey The key from the Python client
 * @param {string} group The group the client claims to be
 * @returns {Promise<boolean>} True if valid, false if not
 */
async function validateKey(apiKey, group) {
    try {
        const docRef = keysCollection.doc(apiKey); // Use the API key as the document ID
        const doc = await docRef.get();

        if (!doc.exists) {
            console.warn(`Auth Error: Key ${apiKey} not found.`);
            return false;
        }

        const data = doc.data();

        if (data.worker_group !== group) {
            console.warn(`Auth Error: Key ${apiKey} is for group ${data.worker_group}, not ${group}.`);
            return false;
        }

        if (data.is_active !== true) {
            console.warn(`Auth Error: Key ${apiKey} is not active.`);
            return false;
        }

        return true; // Key is valid, active, and for the correct group
    } catch (err) {
        console.error("Firestore validation error:", err.message);
        return false;
    }
}

/**
 * Adds a new API key to the database.
 * @param {string} apiKey The new key
 * @param {string} group The group this key belongs to
 * @returns {Promise<void>}
 */
async function addKey(apiKey, group) {
    try {
        const docRef = keysCollection.doc(apiKey); // Use the new key as the unique document ID
        await docRef.set({
            worker_group: group,
            is_active: true,
            created_at: new Date()
        });
        console.log(`A new key has been added for group ${group}`);
    } catch (err) {
        console.error("Error adding key to Firestore:", err.message);
        throw err; // Re-throw to be caught by the server
    }
}

module.exports = {
    validateKey,
    addKey
};