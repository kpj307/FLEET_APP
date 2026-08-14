import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import styles from "../styles/PaymentCallback.module.css";

export default function PaymentCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const [status, setStatus] = useState("processing");
    const [message, setMessage] = useState(
        "Verifying your payment..."
    );

    useEffect(() => {
        const verifyPayment = async () => {
            const paymentStatus =
                searchParams.get("status");

            const txRef =
                searchParams.get("tx_ref");

            const transactionId =
                searchParams.get("transaction_id");

            if (!txRef) {
                setStatus("error");
                setMessage(
                    "Payment reference was not provided."
                );
                return;
            }

            if (paymentStatus === "cancelled") {
                setStatus("cancelled");
                setMessage(
                    "Payment was cancelled."
                );
                return;
            }

            if (paymentStatus === "failed") {
                setStatus("failed");
                setMessage(
                    "Payment was not successful."
                );
                return;
            }

            if (!transactionId) {
                setStatus("error");
                setMessage(
                    "Transaction ID was not provided."
                );
                return;
            }

            try {
                const response = await api.get(
                    `/api/payments/status/${encodeURIComponent(
                        txRef
                    )}/`,
                    {
                        params: {
                            transaction_id:
                                transactionId,
                        },
                    }
                );

                if (
                    response.data.status ===
                    "successful"
                ) {
                    setStatus("success");

                    setMessage(
                        `Your ${response.data.plan} plan is now active.`
                    );

                    // Give the user a moment to see
                    // the confirmation before going
                    // back to the dashboard.
                    setTimeout(() => {
                        navigate("/dashboard");
                    }, 2000);

                    return;
                }

                setStatus("pending");

                setMessage(
                    "Payment is still being processed. Please wait a moment."
                );
            } catch (error) {
                console.error(
                    "Payment verification failed:",
                    error
                );

                setStatus("error");

                setMessage(
                    error.response?.data?.detail ||
                    "We could not verify your payment. Please contact support if you were charged."
                );
            }
        };

        verifyPayment();
    }, [searchParams, navigate]);

    return (
        <div className={styles.container}>
            <div className={styles.card}>
                {status === "processing" && (
                    <>
                        <h1>
                            Verifying payment
                        </h1>

                        <p>{message}</p>

                        <div
                            className={
                                styles.spinner
                            }
                        />
                    </>
                )}

                {status === "success" && (
                    <>
                        <h1>
                            Payment successful
                        </h1>

                        <p>{message}</p>

                        <p>
                            Redirecting to your
                            dashboard...
                        </p>
                    </>
                )}

                {status === "pending" && (
                    <>
                        <h1>
                            Payment processing
                        </h1>

                        <p>{message}</p>
                    </>
                )}

                {status === "failed" && (
                    <>
                        <h1>
                            Payment failed
                        </h1>

                        <p>{message}</p>

                        <button
                            onClick={() =>
                                navigate(
                                    "/pricing"
                                )
                            }
                        >
                            Return to pricing
                        </button>
                    </>
                )}

                {status === "cancelled" && (
                    <>
                        <h1>
                            Payment cancelled
                        </h1>

                        <p>{message}</p>

                        <button
                            onClick={() =>
                                navigate(
                                    "/pricing"
                                )
                            }
                        >
                            Return to pricing
                        </button>
                    </>
                )}

                {status === "error" && (
                    <>
                        <h1>
                            Payment verification problem
                        </h1>

                        <p>{message}</p>

                        <button
                            onClick={() =>
                                navigate(
                                    "/pricing"
                                )
                            }
                        >
                            Return to pricing
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}