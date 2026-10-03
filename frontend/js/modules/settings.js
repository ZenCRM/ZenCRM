/* Keep the settings feature at its original position in ZenModules. */
window.ZenModules = window.ZenModules || {};
window.ZenModules.settings = function () {
    const settings = {};
    const factories = [window.ZenSettings.state, window.ZenSettings.permissions, window.ZenSettings.general, window.ZenSettings.translations, window.ZenSettings.appearance, window.ZenSettings.fields, window.ZenSettings.helpdesk, window.ZenSettings.email, window.ZenSettings.navigation];
    for (const factory of factories) {
        Object.defineProperties(settings, Object.getOwnPropertyDescriptors(factory()));
    }
    return settings;
};
