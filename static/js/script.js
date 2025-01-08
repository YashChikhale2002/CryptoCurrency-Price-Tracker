// Initialize SocketIO connection
const socket = io();

// Listen for price updates
socket.on("price_update", (data) => {
    const { symbol, price, volume, change } = data;

    // Update price in the DOM
    const priceValue = document.getElementById(`price-value-${symbol}`);
    const volumeValue = document.getElementById(`volume-value-${symbol}`);
    const changeValue = document.getElementById(`change-value-${symbol}`);

    if (priceValue && volumeValue && changeValue) {
        const existingPrice = parseFloat(priceValue.textContent.replace(/[^0-9.-]+/g,""));

        // Update price text
        priceValue.textContent = `$${price.toFixed(5)}`;
        volumeValue.textContent = `Volume: ${volume.toFixed(2)}`;
        changeValue.textContent = `Change: ${change > 0 ? '+' : ''}${change.toFixed(2)}%`;

        // Change text color based on price change
        if (existingPrice) {
            if (price > existingPrice) {
                priceValue.classList.remove('text-red-500');
                priceValue.classList.add('text-green-500');
            } else if (price < existingPrice) {
                priceValue.classList.remove('text-green-500');
                priceValue.classList.add('text-red-500');
            }
        }
    }
});
