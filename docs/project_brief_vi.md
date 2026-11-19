# Dự án Quản trị doanh thu: Khách sạn nên bán vượt bao nhiêu phòng? (Bản chi tiết)

**Chủ đề:** Kinh doanh, vận hành và quản trị doanh thu (revenue management) trong ngành khách sạn. Bạn dùng dữ liệu gần 120.000 lượt đặt phòng có thật của hai khách sạn ở Bồ Đào Nha (2015–2017) để trả lời một câu hỏi mà mọi khách sạn đều phải quyết định mỗi đêm.

**Bạn sẽ làm gì:** Khám phá dữ liệu bằng biểu đồ, tự xây một mô hình dự đoán khách nào sẽ hủy phòng vào phút chót, biến dự đoán đó thành quyết định "đêm nay bán vượt bao nhiêu phòng", rồi kiểm tra các quyết định đó trên 8 tháng dữ liệu mà mô hình chưa từng thấy. Cuối cùng, bạn biến toàn bộ kết quả thành một trang web tương tác.

**Bạn sẽ học được gì:**

- **Kiến thức kinh doanh:** quản trị doanh thu, chi phí cơ hội, bài toán "người bán báo" (newsvendor), đánh đổi giữa doanh thu và rủi ro, trải nghiệm khách hàng.
- **Kỹ năng dữ liệu:** Python, xử lý bảng dữ liệu, vẽ biểu đồ, học máy cơ bản, mô phỏng, làm app web, dùng Git và GitHub.
- **Tư duy nghiên cứu:** đặt câu hỏi, kiểm chứng bằng dữ liệu, tự phát hiện và sửa sai.

**Đầu ra:** một app web chạy thật có link chia sẻ, một báo cáo nghiên cứu và một kho code trên GitHub, sẵn sàng đưa vào hồ sơ du học.

**Thời lượng:** 14 tuần, khoảng 2–4 giờ mỗi tuần, có mentor kèm từ đầu đến cuối.

## Dự án này là gì?

Hãng hàng không và khách sạn đều **bán vượt** (overbooking): bán nhiều chỗ hơn số chỗ thật, vì biết chắc sẽ có người hủy vào phút chót hoặc không đến. Nếu không bán vượt, phòng trống, mất tiền. Nếu bán vượt quá tay, đêm đó khách đến đông hơn số phòng, khách sạn phải đưa khách sang khách sạn khác (gọi là **"walk" khách**): trả tiền phòng ở nơi khác, tiền xe, lời xin lỗi, và có thể mất luôn khách đó.

Vậy mỗi đêm, khách sạn nên bán vượt bao nhiêu phòng? Đó là câu hỏi bạn sẽ trả lời, bằng tiền thật (euro) và bằng số khách bị "walk".

**Điều đặc biệt của dự án:** bạn không dừng ở "dự đoán ai hủy phòng" như hàng nghìn bài trên mạng. Bạn đi tiếp đến **quyết định** và đo xem quyết định đó kiếm hay mất bao nhiêu tiền. Trên đường đi, bạn sẽ gặp một điều bất ngờ: mô hình "giỏi" nhất chưa chắc mang lại quyết định tốt nhất.

## Câu hỏi bạn sẽ trả lời

**Câu hỏi lớn:** Mỗi đêm, khách sạn nên bán vượt bao nhiêu phòng, và làm vậy kiếm thêm bao nhiêu tiền so với không bán vượt?

Bạn sẽ đi qua 4 câu hỏi nhỏ, mỗi câu là một chặng:

1. **Hủy phòng nào mới làm mất tiền?** Khách hủy khi nào? Bao nhiêu phần trăm hủy vào tuần cuối, khi phòng không kịp bán lại?
2. **Có đoán trước được không?** Từ thông tin lúc đặt phòng (đặt trước bao lâu, kênh đặt, loại đặt cọc…), mô hình đoán được ai sẽ hủy vào phút chót đến mức nào?
3. **Đêm nay bán vượt bao nhiêu?** Dùng quy tắc "người bán báo" để cân bằng giữa phòng trống và khách bị "walk".
4. **Quy tắc nào kiếm nhiều tiền nhất?** So sánh nhiều quy tắc trên dữ liệu năm 2017, tính bằng euro và số khách bị "walk".

## Dữ liệu bạn sẽ dùng

Bộ [Hotel booking demand](https://doi.org/10.1016/j.dib.2018.11.126) (Antonio, de Almeida & Nunes, 2019) lấy từ hệ thống quản lý của hai khách sạn thật: một khách sạn thành phố ở Lisbon và một khu nghỉ dưỡng ở Algarve. Dữ liệu miễn phí, khoảng 17 MB, tải được không cần tài khoản ([bản TidyTuesday](https://github.com/rfordatascience/tidytuesday/tree/master/data/2020/2020-02-11)).

- **119.390 lượt đặt phòng**, khách đến từ tháng 7/2015 đến tháng 8/2017, gồm cả những lượt đã bị hủy.
- **32 thông tin** cho mỗi lượt đặt.

| Thông tin | Ý nghĩa đơn giản |
| --- | --- |
| Khách sạn | Khách sạn thành phố hay khu nghỉ dưỡng |
| Đặt trước bao lâu (lead time) | Số ngày giữa lúc đặt và lúc đến |
| Ngày đến, số đêm | Khách ở từ ngày nào, bao nhiêu đêm |
| Giá phòng trung bình (ADR) | Bao nhiêu euro mỗi đêm |
| Loại đặt cọc | Không cọc, cọc không hoàn lại, cọc có hoàn lại |
| Phân khúc, kênh bán | Khách đặt qua đại lý du lịch, trực tiếp, doanh nghiệp, đoàn… |
| Lịch sử khách | Đã từng hủy bao nhiêu lần, có phải khách quen không |
| Trạng thái và ngày trạng thái | Đã ở, đã hủy (hủy ngày nào), hay không đến |

**Một điều cần cẩn thận:** vài cột chỉ được ghi *sau* khi đặt phòng, ví dụ số lần thay đổi đặt phòng hay chỗ đậu xe. Dùng chúng để dự đoán là "gian lận vô tình". Phát hiện những cái bẫy kiểu này là kỹ năng của một nhà phân tích thật, và là chất liệu rất tốt cho bài luận.

## Kiến thức kinh doanh bạn sẽ học

| Khái niệm | Hiểu đơn giản | Ví dụ trong dự án |
| --- | --- | --- |
| Quản trị doanh thu | Bán đúng phòng, đúng giá, đúng lúc | Vì sao khách sạn và hãng bay đều bán vượt |
| Chi phí cơ hội | Tiền mất vì không làm một việc | Một phòng trống là mất một đêm tiền phòng |
| Bài toán người bán báo | Đặt hàng bao nhiêu khi không biết trước nhu cầu | Bán vượt đến khi rủi ro "walk" khách cân bằng với rủi ro phòng trống |
| Đánh đổi rủi ro | Kiếm thêm tiền thì phải chịu thêm rủi ro | Bán vượt nhiều: thêm doanh thu nhưng nhiều khách bị "walk" |
| Dữ liệu thay đổi theo thời gian | Quá khứ không còn giống hiện tại | Khách năm 2017 hủy ít hơn hẳn năm 2015 |
| Kiểm tra ngược (backtest) | Thử quy tắc trên dữ liệu quá khứ như thể đang sống ở thời điểm đó | Áp từng quy tắc cho từng đêm năm 2017 |

Công thức quan trọng nhất chỉ cần toán cấp 2. Nếu "walk" một khách tốn gấp w lần giá phòng, khách sạn nên bán vượt x phòng sao cho

```latex
P(\text{số phòng mất vào phút chót} \le x) \approx \frac{1}{1 + w}
```

Ví dụ w = 3: chỉ bán vượt đến mức mà 25% số đêm có ít phòng bị hủy hơn thế. Vì sai một bên tốn gấp ba bên kia, khách sạn nên thận trọng.

## App của bạn trông như thế nào

| Trang | Người xem làm gì | Người xem thấy gì |
| --- | --- | --- |
| Rủi ro của một lượt đặt | Nhập thông tin một lượt đặt: khách sạn, đặt trước bao lâu, kênh, đặt cọc… | Khả năng lượt đặt này bị hủy vào phút chót, và yếu tố nào đẩy rủi ro lên |
| Quyết định đêm nay | Chọn một đêm năm 2017, chi phí "walk" khách, mức rủi ro chấp nhận được | Nên bán vượt bao nhiêu phòng, khả năng phải "walk" khách, và đêm đó thực tế ra sao |
| So sánh các quy tắc | Chọn chi phí "walk" khách | Mỗi quy tắc kiếm hay mất bao nhiêu tiền, "walk" bao nhiêu khách |
| Khám phá dữ liệu | Lọc theo khách sạn, loại cọc, kênh bán | Tỷ lệ hủy và hủy phút chót theo từng nhóm, theo thời gian |

## Cách làm chi tiết

Bạn chưa cần hiểu hết ngay, mentor sẽ giải thích từng bước khi đến chặng đó.

### Bước 1: Làm sạch dữ liệu và định nghĩa đúng vấn đề

- Bỏ các dòng vô lý: không có khách nào, giá phòng âm, giá phòng hàng nghìn euro một đêm.
- **Định nghĩa "mất phòng phút chót":** hủy trong vòng 7 ngày trước ngày đến, hoặc không đến. Chỉ xét những lượt đặt còn hiệu lực 7 ngày trước ngày đến, vì đó là lúc khách sạn quyết định.
- **Bỏ các cột "nhìn trước tương lai"** như số lần thay đổi đặt phòng, loại phòng được xếp, chỗ đậu xe.

### Bước 2: Dự đoán

- **Mô hình 1, hồi quy logistic:** đơn giản, giải thích được từng yếu tố.
- **Mô hình 2, gradient boosting:** mạnh hơn, bắt được quan hệ phức tạp.
- **Chia theo thời gian:** học trên 2015–2016, kiểm tra trên 2017.
- Đo **AUC** (mô hình xếp hạng rủi ro tốt đến đâu) và **độ hiệu chuẩn** (nói 10% thì có đúng khoảng 10% không).

### Bước 3: Từ lượt đặt sang từng đêm

Một lượt đặt 3 đêm chiếm phòng trong 3 đêm. Với mỗi khách sạn, mỗi đêm: bao nhiêu phòng đã bán, bao nhiêu phòng mất vào phút chót. Dữ liệu không cho biết khách sạn có bao nhiêu phòng, nên bạn phải tự ước lượng.

### Bước 4: Quyết định và kiểm tra ngược

- Mỗi đêm năm 2017, mỗi quy tắc chọn số phòng bán vượt chỉ bằng thông tin có ở thời điểm đó.
- So sánh ít nhất 4 quy tắc: không bán vượt; một con số cố định; dùng mô hình; dùng tỷ lệ hủy của 4 tuần gần nhất.
- Tính tiền kiếm thêm, số đêm phải "walk" khách, số khách bị "walk". Thử với chi phí "walk" từ 1 đến 5 lần giá phòng.

### Bước 5: Nói chuyện với một khách sạn thật

Hẹn gặp quản lý hoặc lễ tân một khách sạn ở Hà Nội (15–20 phút): họ có bán vượt không, quyết định thế nào, "walk" một khách tốn bao nhiêu, họ chấp nhận "walk" khách thường xuyên đến mức nào. So sánh với giả định của bạn.

## Kế hoạch 14 tuần

| Tuần | Học gì | Làm gì | Nộp |
| --- | --- | --- | --- |
| 1 | VS Code, Python cơ bản, Git | Cài đặt môi trường, tạo kho GitHub | Kho GitHub có README đầu tiên |
| 2 | pandas: đọc, lọc, lưu dữ liệu | Tải dữ liệu, làm sạch, lưu Parquet | File dữ liệu sạch + bảng giải thích cột |
| 3 | Vẽ biểu đồ; thống kê mô tả | Khách hủy khi nào, theo kênh, theo loại cọc | Notebook với 6–8 biểu đồ có nhận xét |
| 4 | Định nghĩa đúng vấn đề | Nhãn "mất phòng phút chót"; xu hướng theo tháng | Biểu đồ tỷ lệ mất phòng phút chót theo tháng + 2–3 giả thuyết |
| 5 | Học máy là gì; hồi quy logistic | Chọn đầu vào, chia theo thời gian, mô hình 1 | Mô hình logistic + AUC ban đầu |
| 6 | Gradient boosting; cột "nhìn trước tương lai" | Mô hình 2; thử thêm/bớt cột rò rỉ | Bảng so sánh, giải thích vì sao bỏ cột |
| 7 | AUC, độ hiệu chuẩn | Mô hình đoán đúng tỷ lệ năm 2017 không? | Biểu đồ hiệu chuẩn + nhận xét |
| 8 | Bài toán người bán báo | Từ lượt đặt sang từng đêm; ước lượng số phòng | Đường "tiền kiếm thêm" theo số phòng bán vượt |
| 9 | Kiểm tra ngược | So sánh các quy tắc trên 2017; thử chi phí "walk" khác nhau | Bảng kết quả + 3–5 phát hiện chính |
| 10 | Streamlit cơ bản | Khung app, trang "Rủi ro của một lượt đặt" | App chạy trên máy với trang đầu tiên |
| 11 | Biểu đồ tương tác | Trang "Quyết định đêm nay" và "So sánh các quy tắc" | App 3 trang |
| 12 | Kiểm thử, triển khai | Trang "Khám phá dữ liệu", viết test, đưa app lên Streamlit Cloud | Link app công khai |
| 13 | Viết báo cáo khoa học | Báo cáo tiếng Anh, có mục "những lỗi tôi đã gặp"; phỏng vấn khách sạn | Bản nháp báo cáo |
| 14 | Trình bày dự án | Hoàn thiện README, sửa báo cáo, chuẩn bị trình bày dự án | Bộ hồ sơ dự án hoàn chỉnh |

Các tuần 8 và 9 thường nặng nhất. Nếu cần, có thể giãn thành 16 tuần.

## Công cụ bạn sẽ học dùng

| Công cụ | Dùng để làm gì |
| --- | --- |
| VS Code | Phần mềm viết code chính |
| Python, pandas | Đọc, lọc, tính toán trên bảng dữ liệu |
| Matplotlib, Plotly | Vẽ biểu đồ tĩnh và tương tác |
| scikit-learn | Xây mô hình dự đoán |
| SciPy | Phân phối xác suất cho quyết định bán vượt |
| Streamlit | Biến code Python thành trang web tương tác |
| Git, GitHub | Lưu mọi thay đổi và công khai dự án |

## Cấu trúc kho code

```
hotel-overbooking/
├── src/hotel_ob/          # Code chính, chia theo việc
│   ├── config.py          #   Đường dẫn, danh sách cột, ngày chia dữ liệu, chi phí "walk"
│   ├── data.py            #   Đọc, làm sạch, gắn nhãn
│   ├── features.py        #   Đầu vào cho mô hình
│   ├── model.py           #   Huấn luyện và đánh giá mô hình
│   ├── nights.py          #   Từ lượt đặt sang từng đêm
│   └── policy.py          #   Quyết định bán vượt và kiểm tra ngược
├── scripts/               # Chạy từ đầu đến cuối
├── app/                   # Trang web Streamlit (4 trang)
├── notebooks/             # Phân tích khám phá, viết như bài hướng dẫn
├── models/ results/       # Mô hình và bảng kết quả
├── report/                # Báo cáo nghiên cứu + biểu đồ
├── tests/                 # Kiểm tra tự động
└── README.md
```

## Tiêu chí hoàn thành

**Dữ liệu và phân tích**

- [ ] Nhãn là "mất phòng phút chót", không phải mọi lượt hủy
- [ ] Không có cột "nhìn trước tương lai" nào trong đầu vào của mô hình
- [ ] Mỗi biểu đồ có tiêu đề, đơn vị và một câu nhận xét

**Mô hình và quyết định**

- [ ] Dữ liệu được chia theo thời gian
- [ ] Giải thích được quy tắc người bán báo bằng lời của mình
- [ ] So sánh ít nhất 4 quy tắc bằng euro và số khách bị "walk"
- [ ] Thử ít nhất 3 mức chi phí "walk" khách khác nhau

**App**

- [ ] Đủ 4 trang, mở bằng link công khai
- [ ] Người không biết code dùng được mà không cần hướng dẫn
- [ ] Có kiểm tra tự động, app chạy không lỗi

**Báo cáo và trình bày**

- [ ] Báo cáo tiếng Anh có đủ: câu hỏi, dữ liệu, cách làm, phát hiện, hạn chế
- [ ] Có mục "những lỗi tôi đã gặp và cách sửa"
- [ ] Có tóm tắt cuộc nói chuyện với một khách sạn thật
- [ ] Mỗi phát hiện chính có một con số cụ thể
- [ ] README trên GitHub có hướng dẫn chạy, link app, link báo cáo

## Dùng cho hồ sơ thế nào

**Phù hợp apply ngành:** Quản trị kinh doanh, Quản trị khách sạn và du lịch, Vận hành và chuỗi cung ứng, Kinh tế, Thống kê, Toán ứng dụng, Data Science.

| Phần hồ sơ | Cách dùng dự án |
| --- | --- |
| Hoạt động ngoại khóa | Một dòng có con số, ví dụ "Phân tích 119.000 lượt đặt phòng để quyết định khách sạn nên bán vượt bao nhiêu phòng; phát hiện…" |
| Bài luận "Why this major" | Kể lúc mô hình của bạn làm khách sạn *mất* tiền, và bạn tìm ra lý do |
| Portfolio | Gửi link app và báo cáo để người đọc tự dùng thử |
| Phỏng vấn | Một chủ đề bạn nói được 10 phút, có số liệu và cuộc nói chuyện với khách sạn thật |

Không dự án nào đảm bảo kết quả trúng tuyển. Nhưng một sản phẩm thật, do chính bạn làm và giải thích được, giúp hồ sơ khác biệt.

## Câu hỏi thường gặp

**Mình chưa biết lập trình, có làm được không?** Được. Mentor hướng dẫn từ bước cài đặt đầu tiên.

**Máy tính cần mạnh cỡ nào?** Laptop thông thường là đủ. Dữ liệu chỉ 17 MB, toàn bộ phân tích chạy trong khoảng một phút.

**Trên mạng đã có nhiều bài về bộ dữ liệu này, có bị trùng không?** Phần lớn chỉ dừng ở "dự đoán ai hủy phòng", và nhiều bài vô tình dùng cột "nhìn trước tương lai". Dự án của bạn đi tiếp đến quyết định bán vượt và đo bằng tiền, nên câu chuyện và phát hiện là của riêng bạn.
