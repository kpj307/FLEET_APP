import { useNavigate } from "react-router-dom";
import Form from "../components/Form"

function Login() {
    const navigate = useNavigate();

    return ( <Form route="/api/token/" method="login" /> )

}

export default Login