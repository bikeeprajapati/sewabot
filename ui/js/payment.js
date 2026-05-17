    // ── eSewa payment flow ───────────────────────────────────
    const PaymentManager = {
    async initiate(jobId, clientId) {
        try {
        const data = await PaymentsAPI.initiate(jobId, clientId);

        // Build and auto-submit eSewa form
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form';

        const fields = data.payment_data;
        Object.entries(fields).forEach(([key, value]) => {
            const input = document.createElement('input');
            input.type  = 'hidden';
            input.name  = key;
            input.value = value;
            form.appendChild(input);
        });

        document.body.appendChild(form);
        form.submit();

        } catch (err) {
        showToast(`Payment error: ${err.message}`, 'error');
        }
    }
    };